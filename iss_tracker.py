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
from flask import Flask, request
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
    Fetches ISS data from NASA and stores it in Redis using keys which are the EPOCH. Each state vector and its information are stored in a seperate key.

    Args:
        None
    
    Returns:
        None
    """
    ISS_URL = "https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml"
    
    # Check if Redis already has ISS data
    if rd.keys():
        logging.info("Redis already contains ISS data.")
        return False
    
    try:
        logging.info("Fetching data from NASA...")
        response = requests.get(ISS_URL)

        logging.info(f"Response status code: {response.status_code}")
        
        if response.status_code != 200:
            logging.error(f"Failed to fetch data. Status code: {response.status_code}")
            return
        
        # Parse the XML data
        iss_data = xmltodict.parse(response.text)
        logging.info(f"Data parsed successfully: {len(iss_data)} entries")
        
        state_vectors = iss_data['ndm']['oem']['body']['segment']['data']['stateVector']
        logging.info(f"State vectors extracted: {len(state_vectors)}")
        
        if not state_vectors:
            logging.error("No state_vector data.")
            return

        # Iterate over the state vectors and store each one in Redis with a unique EPOCH key
        for state_vector in (state_vectors):
            redis_key = state_vector['EPOCH']

            # Convert to json and dump as seen in class
            state_vector_json = json.dumps(state_vector)

            rd.set(redis_key, state_vector_json)
            logging.info(f"State vector stored in Redis with key: {redis_key}")

    except Exception as e:
        logging.error(f"Error during data fetching: {e}")

def fetch_data_from_redis() -> list[dict]:
    """
    This function fetches all data from Redis and returns it as a list of dictionaries.

    Args:
        None

    Returns:
        state_vectors (list[dict]): All of the state vector data as a list of dictionaries
    """
    try:
        # Get all keys from Redis
        keys = rd.keys()  
        state_vectors = []

        for key in keys:
            data = rd.get(key.decode('utf-8')) 
            state_vector = json.loads(data.decode('utf-8'))
            state_vectors.append(state_vector)

        logging.info(f"Fetched {len(state_vectors)} state vectors from Redis so far.")

        return state_vectors
    except Exception as e:
        logging.error(f"Error during Redis data fetch: {e}")

def calc_closest_speed(data_list_of_dicts: List[dict], x_key_speed: str, y_key_speed: str, z_key_speed: str) -> Tuple[float, dict, dict]:
    """
    This function calculates and returns the most recent speed of the ISS compared to our time now, the time from the data set that is closest to when the script was ran, and the dictionary for that data set

    Args:
        data_list_of_dicts (List[dict]): A list of dictionaries of all the information of each time stamp of the ISS created when reading the requested data.

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
    Returns all the datasets or a limited amount of epochs and their state vector datas

    Args:
        none

    Query Parameters:
        limit (int): Number of epochs to return
        offset (int): Number of epochs to skip before starting

    Returns:
        The state vectors either with or without filtered epochs and their data
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
    Returns the state vector for a specific epoch requested

    Args:
        epoch (str): The epoch timestamp we want to retrieve state vectors from

    Returns:
        result (str): The state vector data of a the particular epoch being requested
    """

    # Retrieve data of the specific epoch from the matching epoch key
    epoch_match = rd.get(epoch)

    if not epoch_match:
        logging.error("No data available")
        return "Error"
    
    # Load the data into a Python dictionary
    try:
        epoch_match = json.loads(epoch_match)

    except Exception as e:
        logging.error(f"Failed to decode the data: {e}")
        return "Error"
    
    logging.debug("Matching epochs...")

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
        logging.error(f"Invalid data: {e}")
        return "Invalid data"

    return result

@app.route('/epochs/<epoch>/speed', methods = ['GET'])
def get_epoch_speed(epoch: str) -> str:
    """
    This function calculates the instantaneous speed for a specific epoch being requested

    Args:
        epoch (str): The epoch timestamp to retrieve the instantaneous speed from

    Returns:
        speed (str): The calculated instantaneous speed in km/s of a certain epoch
    """

    # Retrieve data for specific epoch 
    epoch_data = rd.get(epoch)

    if not epoch_data:
        logging.error("No data available")
        return "Error"
    
    # Load the data into a Python dictionary
    try:
        epoch_data = json.loads(epoch_data)
    except Exception as e:
        logging.error(f"Failed to decode the data: {e}")
        return "Error"
    
    logging.debug("Matching epochs...")

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
        logging.error(f"Invalid data: {e}")
        return "Invalid data"

@app.route('/now', methods = ['GET'])
def get_current_state_vector_and_speed() -> str:
    """
    Returns the state vector, latitude, longitude, altitude, geoposition, and instantaneous speed for the nearest epoch to current time

    Args:
        None

    Returns:
        response (str): This function returns the state vectors, instantaneous speed, latitude, longitude, altitude and geoposition for the Epoch that is nearest in time as a string
    """

    # Retrieve data
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

    geoloc_address = "Unknown"

    # Compute location (latitude, longitude, altitude), Code from coe-332 readthedocs
    try:
        this_epoch = time.strftime('%Y-%m-%d %H:%M:%S', time.strptime(closest_epoch['EPOCH'][:-5], '%Y-%jT%H:%M:%S'))
        cartrep = coordinates.CartesianRepresentation([x, y, z], unit=units.km)
        gcrs = coordinates.GCRS(cartrep, obstime=this_epoch)
        itrs = gcrs.transform_to(coordinates.ITRS(obstime=this_epoch))
        loc = coordinates.EarthLocation(*itrs.cartesian.xyz)

        lat, lon, alt = loc.lat.value, loc.lon.value, loc.height.value
    except Exception as e:
        logging.error(f"Error calculating location: {e}")
        return

    try:
        geocoder = Nominatim(user_agent="iss_tracker")
        geoloc = geocoder.reverse((lat, lon), zoom=15, language="en")
        geoloc_address = geoloc.address 
    except Exception as e:
        logging.error(f"GeoPy error: {e}")

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

    # This code is from the coe-332 readthedocs
    # Retrieve data
    epoch_data = rd.get(epoch)

    if not epoch_data:
        logging.error("No data available")
        return "Error"
    
    # Load the data to a Python dictionary
    try:
        epoch_data = json.loads(epoch_data)
    except Exception as e:
        logging.error(f"Failed to decode data: {e}")
        return "Error"
    
    try: 
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
            geoloc_address = geoloc.address
        except Exception as e:
            logging.error(f"Error: {e}")
            return

        logging.info(f"Location for epoch {epoch} calculated successfully.")

        return {
            "Latitude": lat,
            "Longitude": lon,
            "Altitude": alt,
            "Geolocation": geoloc_address
        }
    
    except Exception as e:
        logging.error(f"Error: {e}")
        return

if __name__ == '__main__':
    # Store data in Redis
    fetch_data()
    app.run(debug=True, host='0.0.0.0')
