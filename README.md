# NASA ISS Trajectory: A Speed, Velocity, and Position Summary

## Objective:
This project was created to utilize a Flask web application to analyze ISS data regarding its speed, velocities, and positions at certain time stamps based on a 15-day span of data about its trajectory, specifically focusing on the results closest to our most recent script call and any EPOCH we want to analyze based on the route we provide. This data is crucial for understanding the ISS’s movement in real time, supporting applications in aerospace analysis, orbital predictions, and mission planning. Overall, this aims to help us gain a better understanding of the ISS and its trajectory.

## Contents: 
This project contains the following files and directories:
- iss_tracker.py
- test_iss_tracker.py
- requirements.txt: A file listing the required Python packages for the project, ensuring a consistent environment.
- Dockerfile: The file used to build a Docker container for deploying the Flask app.
- System Diagram
- Docker-compose

## Scripts:
This folder contains two scripts for the Flask web application:
1. **iss_tracker.py (main script)**
This script contains routes that use the GET method to retrieve data you want to analyze or interpret. Based on your route, the script will either retrieve the whole data set or return certain data sets based on any query parameters you input. Beyond those functionalities, the script can also return the state vectors for a specific EPOCH, the instantaneous speed of a specific EPOCH, and the state vectors/instantaneous speed at the closest timestamp the route was called. Other functionalities include returning a specific epoch's latitude, longitude, and geospatial location or the closest epoch to the time the script was called. 
3. **test_iss_tracker.py (unit test for the main script)**
This script contains unit tests using `pytest` for the functions in `iss_tracker.py`. The tests cover cases such as invalid data, calculating the average/closest velocity, and managing missing or incorrect data.

## Logging:
Please note that the current logging level is set to ERROR. If you wish to change this open `iss_tracker.py` with a text or code editor and replace the ERROR in logging.basicConfig to whichever level you want to run. (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## System Diagram:
<img src="ISSTracker_System_Diagram.png" alt="My Image" width="800">
The system diagram above depicts how the scripts and files in the directory interact with one another. It depicts how the container is ran and describes how the Flask web API interacts with the user to return data summaries from data from the web. 

## Data Origin:
To access the data used in this homework, please use this link: https://spotthestation.nasa.gov/trajectory_data.cfm. The data presented are given in both `txt` and `XML` formats. To view them, please download them onto your computer. The ISS trajectory data is publicly available and maintained by the ISS Trajectory Operations and Planning Officer (TOPO) at NASA’s Johnson Space Center. The ISS’s position is continuously tracked, and its predicted trajectory is updated approximately three times a week to ensure accuracy. This data is critical for maintaining communication links, planning vehicle rendezvous, and avoiding potential collisions. 
   
## Building container and running code (Username is your Docker Hub Username):
1. **Build Docker image**: First, make sure everything in this homework is in the same directory. In the terminal, please run the command: `docker build -t username/flask-iss_tracker:1.0 .`
2. **Docker Compose**: Next, use a text editor to edit the docker-compose file. Replace the username part of the file with your docker hub username.
3. **Local Data Storage**: In the same director, create a folder called data so that the data written to flask can also be stored on the local machine. 
4. **Run Docker**: To run the container, please run the command: `docker compouse up -d`. The `-d` flags allow the containers to run in the background.
5. **Final Steps**: Now that you have the container running, you must use curl commands to access routes to get the data you want.
6. **Interpret Output**: Here, I will describe the curl commands and what output you should expect.
   - `curl localhost:5000/epochs`: Returns the entire data set in XML format
   - `curl localhost:5000/epochs?limit=int&offset=int`: Returns modified list of Epochs given the query parameters limit and offset in XML format. To do this, place a number in place of the `int` in the curl command. The limit query limits the amount of data outputted, while offset will offset the data being outputted by the amount given.
   - `curl localhost:5000/epochs/<epoch>`: Returns the state vectors for a specific Epoch from the data set. To do this, replace `<epoch>` with a specific epoch you want from the downloaded XML data above.
   - `curl localhost:5000/epochs/<epoch>/speed`: Returns the instantaneous speed of a specific Epoch from the data set in km/s. To do this, replace `<epoch>` with a specific epoch you want from the downloaded XML data above.
   - `/epochs/<epoch>/location`: Returns the latitude, longitude, altitude, and geoposition for a specific Epoch in the data set. To do this, replace `<epoch>` with a specific epoch you want from the downloaded XML data above.
   - `curl localhost:5000/now`: Returns the state vectors as vectors and the instantaneous speed for the EPOCH closest to the call time.
7. **Pytest**: If you want to run the unit tests, please run the command `docker exec -it flask-homework05-app bash` on the command line to attach to the container. Then run `pytest test_iss_tracker.py` to run the unit tests.
8. **Cleanup**: After you are done with the analysis, please run these commands to clean up and remove the container. (ID is the container ID provided after running the container) `docker stop ID` and `docker rm ID`
   
## AI Use (Chat GPT): 
1. AI was used to produce the exception test cases in `test_iss_tracker.py`. I used AI here because I did not know what tests would be reasonable tests for my functions.
3. AI was used to generate the test data information in `test_iss_tracker.py`. I used AI for this because I did not have time to create the data myself.
4. AI was used to convert the given time in the EPOCH to something readable. I used AI for this because I did not know how to do this myself even with research.
5. AI was used in certain areas to generate warning loggings. AI was used for this because I didn't know the proper way to make sure the generated warning was accurate.
6. AI was used to output the list of dictionaries back into XML format because I did not know how to revert to XML formatting.
7. AI was used in the Dockerfile to allow everything to be pip installed at the same time. I used AI for this because I had no knowledge regarding the process of doing this.

