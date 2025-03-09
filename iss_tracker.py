#!/usr/bin/env python3
import xmltodict
import json
import logging
import requests
import math
import socket
import time
from typing import List
from typing import Tuple
from flask import Flask, Response, request
import xml.etree.ElementTree as ET
import xml.dom.minidom
import redis
from astropy import coordinates
from astropy import units
from astropy.time import Time
from geopy.geocoders import Nominatim


# Initialize app
app = Flask(__name__)

# Set logging
format_str=f'[%(asctime)s {socket.gethostname()}] %(filename)s:%(funcName)s:%(lineno)s - %(levelname)s: %(message)s'
logging.basicConfig(level=logging.ERROR, format = format_str)


def get_redis_client():
    return redis.Redis(host='redis-db', port=6379, db=0)

# Initialize Redis client
rd = get_redis_client()

def fetch_data():
    """
    Fetches ISS data from NASA and stores it in Redis using keys.
    """
    ISS_URL = "https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml"
    try:
        logging.info("Fetching data from NASA...")
        response = requests.get(ISS_URL)
        logging.info(f"Response status code: {response.status_code}")
        
        if response.status_code != 200:
            logging.error(f"Failed to fetch data. HTTP status code: {response.status_code}")
            return
        
        # Parse XML data
        iss_data = xmltodict.parse(response.text)
        logging.info(f"Data parsed successfully: {len(iss_data)} entries")
        
        state_vectors = iss_data['ndm']['oem']['body']['segment']['data']['stateVector']
        logging.info(f"State vectors extracted: {len(state_vectors)}")
        
        if not state_vectors:
            logging.error("No state_vector data.")
            return

        # Iterate over the state vectors and store each one in Redis with a unique key
        for i, state_vector in enumerate(state_vectors):
            # Generate a unique key for each state vector (you can use the index and timestamp)
            redis_key = f"iss_state_vector{i}"

            state_vector_json = json.dumps(state_vector)

            rd.set(redis_key, state_vector_json)
            logging.info(f"State vector stored in Redis with key: {redis_key}")

        logging.info(f"Stored {len(state_vectors)} state vectors in Redis.")
    except Exception as e:
        logging.error(f"Error during data fetching: {e}")

@app.route('/get-keys', methods=['GET'])
def get_keys():
    """
    Returns all keys from Redis.
    """
    try:
        keys = rd.keys() 
        decoded_keys = [key.decode('utf-8') for key in keys]  # Decode each key
        return json.dumps(decoded_keys)  # Return the list as a JSON response


    except Exception as e:
        logging.error(f"Error fetching keys from Redis: {e}")
        return 

def fetch_data_from_redis() -> list[dict]:
    """
    Fetches all data from Redis and returns it as a list of dictionaries.
    """
    try:
        keys = rd.keys()  # Get all keys from Redis
        state_vectors = []

        for key in keys:
            data = rd.get(key.decode('utf-8')) 
            state_vector = json.loads(data.decode('utf-8'))
            state_vectors.append(state_vector)
        
        logging.info(f"Fetched {len(state_vectors)} state vectors from Redis.")
        return state_vectors
    except Exception as e:
        logging.error(f"Error during data fetch from Redis: {e}")
    
def calc_average_speed(data_list_of_dicts: List[dict], x_key_speed: str, y_key_speed: str, z_key_speed: str) -> float:
    """
    This function calculates the average speed of the ISS over all the data entries

    Args:
        data_list_of_dicts (List[dict]): A list of dictionaries of all the information of each time stamp of the ISS created when reading the XML requested from the data url.

        x_key_speed (str): The key string containing data about the x position of velocity

        y_key_speed (str): The key string containing data about the y position of velocity

        z_key_speed (str): The key string containing data about the z position of velocity

    Returns:
        average_speed (float): The function returns the average magnitude of velocity (speed) across the whole data set
    """ 

    logging.debug("Computing average speed...")
    
    if not data_list_of_dicts:
        raise ValueError("No data available to compute average speed")
        
    average_speed = 0.

    for i in range(len(data_list_of_dicts)):
        try:
            x_component = float(data_list_of_dicts[i][x_key_speed]["#text"])
            y_component = float(data_list_of_dicts[i][y_key_speed]["#text"])
            z_component = float(data_list_of_dicts[i][z_key_speed]["#text"])

            average_speed += math.sqrt(x_component**2 + y_component**2 + z_component**2)
            logging.debug(f"Row {i}: Successfully added components = {x_component}, {y_component}, {z_component}")

        except (ValueError, KeyError) as e:
            logging.warning(f"Skipping row {i} due to invalid mass data: {e} ")

    average_speed = average_speed / len(data_list_of_dicts)
    logging.debug(f"Calculated average speed: {average_speed} km/s")

    return average_speed
 

def calc_closest_speed(data_list_of_dicts: List[dict], x_key_speed: str, y_key_speed: str, z_key_speed: str) -> Tuple[float, dict, dict]:
    """
    This function calculates and returns the most recent speed of the ISS compared to our time now, the time from the data set that is closest to when the script was ran, and the dictionary for that data set

    Args:
        data_list_of_dicts (List[dict]): A list of dictionaries of all the information of each time stamp of the ISS created when reading the XML requested from the data url.

        x_key_speed (str): The key string containing data about the x position of velocity

        y_key_speed (str): The key string containing data about the y position of velocity

        z_key_speed (str): The key string containing data about the z position of velocity

    Returns:
        closest_speed (float): The function returns the closest magnitude of velocity (speed) to our time now

        closest_time (dict): This is the time closest to when the script was ran for the calculated speed

        closest_epoch (dict): This is the epoch dictionary that is closest to the time the script was ran
    """

    logging.debug("Computing most recent speed...")

    if not data_list_of_dicts:
        raise ValueError("No data available to compute closest speed")
    
    logging.debug("Finding closest current time and corresponding speed...")
    time_now = time.mktime(time.gmtime())

    # Set time and EPOCH
    closest_time = None
    closest_epoch = None
    min_time_diff = float('inf')
    closest_speed = 0.

    for i in range(len(data_list_of_dicts)):
        try:
            epoch_time = time.mktime(time.strptime(data_list_of_dicts[i]["EPOCH"], '%Y-%jT%H:%M:%S.000Z'))

            # Calculating closest time to now using absolute values
            time_diff = abs(epoch_time - time_now)
            
            if time_diff < min_time_diff:
                # Set new closest time and EPOCH
                min_time_diff = time_diff
                closest_time = data_list_of_dicts[i]["EPOCH"]
                closest_epoch = data_list_of_dicts[i]
                
                # Calculate speed for this epoch
                x_component = float(data_list_of_dicts[i][x_key_speed]["#text"])
                y_component = float(data_list_of_dicts[i][y_key_speed]["#text"])
                z_component = float(data_list_of_dicts[i][z_key_speed]["#text"])

                closest_speed = math.sqrt(x_component**2 + y_component**2 + z_component**2)

                logging.debug(f"Updated closest epoch and speed: speed = {closest_speed} km/s")

        except (ValueError, KeyError) as e:
            logging.warning(f"Skipping epoch due to parsing error: {e}")

    return closest_speed, closest_time, closest_epoch

@app.route('/epochs', methods = ['GET'])
def get_epochs() -> list[dict]:
    """
    Returns a dataset of epochs and their state vector datas

    Query Parameters:
        limit (int): Number of epochs to return
        offset (int): Number of epochs to skip before starting

    Returns:
        Response with filtered epochs and their state vector data
    """

    state_vectors = fetch_data_from_redis()
    if state_vectors is None:
        logging.error("Error no data")

    # Handle query parameters for filtering
    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', type=int, default=0)

    logging.debug(f"Query params - limit: {limit}, offset: {offset}")
    
    if offset < 0 or offset >= len(state_vectors):
        logging.warning("Offset is out of range")
        return "Error: Offset out of range", 400

    logging.debug("Applying filters")

    # Apply filtering 
    if limit is not None:
        filtered_data = []
        count = 0

        for i in range(offset, len(state_vectors)):
            if count >= limit:
                break
            filtered_data.append(state_vectors[i])  
            count += 1
        state_vectors = filtered_data  
        
    elif offset is not None: 
        filtered_data = []

        for i in range(offset, len(state_vectors)):
            filtered_data.append(state_vectors[i])  

        state_vectors = filtered_data 

    return state_vectors

@app.route('/epochs/<epoch>', methods = ['GET'])
def get_epoch_data(epoch: str) -> str:
    """
    Returns the state vector for a specific epoch

    Args:
        epoch (str): The epoch timestamp we want to retrieve state vectors from

    Returns:
        result (str): The state vector data of a particular epoch
    """
    state_vectors = fetch_data_from_redis()

    if not state_vectors:
        logging.error("No data available")
        return ("Error no data")
    
    epoch_match = None

    logging.debug("Matching epochs...")

    # Loop through each state vector in the list of state_vectors
    for s_v in state_vectors:
        if s_v["EPOCH"] == epoch:  
            epoch_match = s_v
            # Exit the loop
            break 
    
    logging.debug("Match found")

    try: 
        result = (f"Epoch: {epoch_match['EPOCH']}\n"
                  f"X: {epoch_match['X']['#text']} km\n"
                  f"Y: {epoch_match['Y']['#text']} km\n"
                  f"Z: {epoch_match['Z']['#text']} km\n"
                  f"X_DOT: {epoch_match['X_DOT']['#text']} km/s\n"
                  f"Y_DOT: {epoch_match['Y_DOT']['#text']} km/s\n"
                  f"Z_DOT: {epoch_match['Z_DOT']['#text']} km/s\n")

    except (KeyError, ValueError) as e:
        logging.error(f"Invalid data format: {e}")
        return "Invalid data format"

    return result

@app.route('/epochs/<epoch>/speed', methods = ['GET'])
def get_epoch_speed(epoch: str) -> str:
    """
    This function calculates the instantaneous speed for a specific epoch

    Args:
        epoch (str): The epoch timestamp to retrieve the speed from

    Returns:
        speed (str): The calculated speed in km/s of a certain epoch
    """

    state_vectors = fetch_data_from_redis()
    if not state_vectors:
        logging.error("No data available")
        return ("Error no data")

    epoch_data = None

    logging.debug("Matching epochs...")

    # Loop through each state vector in the list of state_vectors
    for s_v in state_vectors:
        if s_v["EPOCH"] == epoch:  
            epoch_data = s_v
            # Exit the loop
            break 

    logging.debug("Match found")

    try:
        # Get the velocity components
        x_dot = float(epoch_data["X_DOT"]["#text"])
        y_dot = float(epoch_data["Y_DOT"]["#text"])
        z_dot = float(epoch_data["Z_DOT"]["#text"])

        # Calculate the instantaneous speed 
        speed = math.sqrt(x_dot**2 + y_dot**2 + z_dot**2)
        return (f"Instantaneous speed: {speed} (km/s)\n")
    
    except (KeyError, ValueError) as e:
        logging.error(f"Invalid data format: {e}")
        return "Invalid data format"

@app.route('/now', methods = ['GET'])
def get_current_state_vector_and_speed() -> str:
    """
    Return state vector, latitude, longitude, geoposition, and instantaneous speed for the nearest epoch to current time

    Args:
        None

    Returns:
        response (str): This function returns the state vectors, instantaneous speed, latitude, longitude, and geoposition for the Epoch that is nearest in time as a string
    """

    state_vectors = fetch_data_from_redis()
    if state_vectors is None:
        logging.error("Error no data")
        return ("Error no data")
    
    # Logging done by calc_closest_speed
    closest_speed, closest_time, closest_epoch = calc_closest_speed(state_vectors, "X_DOT", "Y_DOT", "Z_DOT")

    x = closest_epoch["X"]["#text"]
    y = closest_epoch["Y"]["#text"]
    z = closest_epoch["Z"]["#text"]
    x_velocity = closest_epoch["X_DOT"]["#text"]
    y_velocity = closest_epoch["Y_DOT"]["#text"]
    z_velocity = closest_epoch["Z_DOT"]["#text"]
    closest_time = time.mktime(time.strptime(closest_epoch["EPOCH"], '%Y-%jT%H:%M:%S.000Z'))
    close_time_readable = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(closest_time))

    # Compute location (latitude, longitude, altitude), Code from coe-332 readthedocs
    try:
        this_epoch = time.strftime('%Y-%m-%d %H:%M:%S', time.strptime(closest_epoch['EPOCH'][:-5], '%Y-%jT%H:%M:%S'))
        cartrep = coordinates.CartesianRepresentation([x, y, z], unit=units.km)
        gcrs = coordinates.GCRS(cartrep, obstime=this_epoch)
        itrs = gcrs.transform_to(coordinates.ITRS(obstime=this_epoch))
        loc = coordinates.EarthLocation(*itrs.cartesian.xyz)

        lat, lon, alt = loc.lat.value, loc.lon.value, loc.height.value
    except Exception as e:
        logging.error(f"Error calculating location with Astropy: {e}")
        return

    try:
        geocoder = Nominatim(user_agent="iss_tracker")
        geoloc = geocoder.reverse((lat, lon), zoom=15, language="en")
        geoloc_address = geoloc.address if geoloc else "Unknown Location"
    except Exception as e:
        logging.error(f"GeoPy error: {e}")
        geoloc_address = "Unknown Location"

    # Create the string
    response = (
        f"Closest time: {close_time_readable}\n"
        f"Closest position as a vector: {x} i + {y} j + {z} k (km)\n"
        f"Closest velocity as a vector: {x_velocity} i + {y_velocity} j + {z_velocity} k (km/s)\n"
        f"Instantaneous speed: {closest_speed} (km/s)\n"
        f"Latitude: {lat}\n"
        f"Longitude: {lon}\n"
        f"Altitude: {alt} km\n"
        f"Geolocation: {geoloc_address}\n"
    )
    return response

@app.route('/epochs/<epoch>/location', methods = ['GET'])
def get_epoch_location(epoch: str) -> str:
    """
    This route returns latitude, longitude, altitude, and geoposition for a given epoch

    Args:
        epoch (str): The string epoch of the epoch you want to find the latitude, longitude, altidude and geoposition of

    Returns:
        The function returns a string that lists the latitude, longitude, altidude and geoposition of the particular epoch in question
    """

    # This code is overall from the coe-332 readthedocs
    try:
        state_vectors = fetch_data_from_redis()
        if not state_vectors:
            logging.error("No data available in Redis.")
            return

        epoch_data = None
        for sv in state_vectors:
            if sv["EPOCH"] == epoch:
                epoch_data = sv
                break

        if epoch_data is None:
            logging.warning(f"Epoch {epoch} not found.")
            return 
        
        x = float(epoch_data['X']['#text'])
        y = float(epoch_data['Y']['#text'])
        z = float(epoch_data['Z']['#text'])

        try:
            this_epoch = time.strftime('%Y-%m-%d %H:%M:%S', time.strptime(epoch_data['EPOCH'][:-5], '%Y-%jT%H:%M:%S'))
        except Exception as e:
            logging.error(f"Error processing epoch timestamp {epoch_data['EPOCH']}: {e}")
            return 
        
        cartrep = coordinates.CartesianRepresentation([x, y, z], unit=units.km)
        gcrs = coordinates.GCRS(cartrep, obstime=this_epoch)
        itrs = gcrs.transform_to(coordinates.ITRS(obstime=this_epoch))
        loc = coordinates.EarthLocation(*itrs.cartesian.xyz)

        lat, lon, alt = loc.lat.value, loc.lon.value, loc.height.value

        # Use GeoPy for geolocation lookup
        try:
            geocoder = Nominatim(user_agent="iss_tracker")
            geoloc = geocoder.reverse((lat, lon), zoom=15, language="en")
            geoloc_address = geoloc.address if geoloc else "Unknown Location"
        except Exception as e:
            logging.error(f"Error: {e}")
            return

        logging.info(f"Location for epoch {epoch} calculated successfully.")

        return {
            "lat": lat,
            "lon": lon,
            "alt": alt,
            "geoloc": geoloc_address
        }
    
    except Exception as e:
        logging.error(f"Unexpected error occurred: {e}")
        return

if __name__ == '__main__':
    # Store data in Redis
    fetch_data()
    app.run(debug=True, host='0.0.0.0')
