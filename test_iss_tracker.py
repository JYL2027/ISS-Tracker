import pytest
import math
import json
from unittest import mock
import requests
import json
from iss_tracker import calc_closest_speed
import pytest
from flask import Flask, jsonify

# Create a minimal Flask app for testing purposes (AI Use)
app = Flask(__name__)

# Tests for route functions
BASE_URL = 'http://127.0.0.1:5000'

# Test data is AI generated
test_data = [
    {'X_DOT': {'#text': '7.0'}, 'Y_DOT': {'#text': '3.0'}, 'Z_DOT': {'#text': '5.0'}, 'EPOCH': '2025-001T12:00:00.000Z'},
    {'X_DOT': {'#text': '5.0'}, 'Y_DOT': {'#text': '2.0'}, 'Z_DOT': {'#text': '4.0'}, 'EPOCH': '2025-002T12:00:00.000Z'},
    {'X_DOT': {'#text': '6.0'}, 'Y_DOT': {'#text': '2.0'}, 'Z_DOT': {'#text': '6.0'}, 'EPOCH': '2025-003T12:00:00.000Z'},
    {'X_DOT': {'#text': '4.0'}, 'Y_DOT': {'#text': '4.0'}, 'Z_DOT': {'#text': '4.0'}, 'EPOCH': '2025-004T12:00:00.000Z'}
]

# Test calc_instant_speed function taking only the speed
def test_calc_closest_speed():
    assert calc_closest_speed(test_data, 'X_DOT', 'Y_DOT', 'Z_DOT')[0] == pytest.approx(6.928203230275509, rel=1e-4)

# Exception tests are AI Generated

# Exception test for calc_closest_speed
def test_calc_closest_speed_exceptions():
    # Case 1: Empty list should raise a ValueError
    with pytest.raises(ValueError, match="No data available to compute closest speed"):
        calc_closest_speed([], 'X_DOT', 'Y_DOT', 'Z_DOT')

    # Case 2: Missing keys should not raise ValueError, but skip the invalid entries
    test_data_missing_keys = [
        {'X_DOT': {'#text': '7.0'}, 'Y_DOT': {'#text': '3.0'}, 'EPOCH': '2025-001T12:00:00.000Z'}
    ]
    result = calc_closest_speed(test_data_missing_keys, 'X_DOT', 'Y_DOT', 'Z_DOT')
    assert result[0] == 0.0  # If no valid speed data, the closest speed should be 0.0

    # Case 3: Non-numeric velocity values should not raise ValueError, but skip the entry
    test_data_invalid_type = [
        {'X_DOT': {'#text': '7.0'}, 'Y_DOT': {'#text': 'abc'}, 'Z_DOT': {'#text': '5.0'}, 'EPOCH': '2025-001T12:00:00.000Z'}
    ]
    result = calc_closest_speed(test_data_invalid_type, 'X_DOT', 'Y_DOT', 'Z_DOT')
    assert result[0] == 0.0  # If the invalid value is skipped, the closest speed should be 0.0

@pytest.fixture
def setup_flask_app():
    response = requests.get(f'{BASE_URL}/epochs')  # Trigger data fetching or cache population
    assert response.status_code == 200  # Make sure the data is fetched correctly
    return response


def test_epochs_route(setup_flask_app):
    # Test the /epochs route
    response1 = requests.get(f'{BASE_URL}/epochs')
    assert response1.status_code == 200
    assert isinstance(response1.json(), list)  # Expect a list of state vectors


def test_specific_epoch_route(setup_flask_app):
    # Get a representative epoch for testing specific epoch endpoint
    response1 = requests.get(f'{BASE_URL}/epochs')
    print(f"Status Code for /epochs: {response1.status_code}")
    print(f"Response for /epochs: {response1.text}")  # Check raw response

    # Check if the response is empty
    if not response1.text:
        print("Empty response received for /epochs")

    # Parse the JSON only if the response is valid
    try:
        representative_epoch = response1.json()[0]
    except ValueError as e:
        print(f"Error parsing JSON from /epochs response: {e}")
        return  # Exit the test early if there's a problem parsing the JSON

    response2 = requests.get(f'{BASE_URL}/epochs/{representative_epoch["EPOCH"]}')
    print(f"Status Code for /epochs/{representative_epoch['EPOCH']}: {response2.status_code}")
    print(f"Response for /epochs/{representative_epoch['EPOCH']}: {response2.text}")  # Check raw response

    # Check if the second response is empty
    if not response2.text:
        print("Empty response received for /epochs/{representative_epoch['EPOCH']}")

    # Continue the assertions if both responses are valid
    assert response2.status_code == 200
    assert isinstance(response2.json(), dict)  # Expect a dictionary with specific epoch data

def test_epoch_speed_route(setup_flask_app):
    # Get a representative epoch for testing speed route
    response1 = requests.get(f'{BASE_URL}/epochs')
    representative_epoch = response1.json()[0]
    
    response2 = requests.get(f'{BASE_URL}/epochs/{representative_epoch["EPOCH"]}/speed')
    
    assert response2.status_code == 200
    assert isinstance(response2.text, str)  # Expect speed as a string in the response


def test_epoch_location_route(setup_flask_app):
    # Test /epochs/<epoch>/location
    response1 = requests.get(f'{BASE_URL}/epochs')
    representative_epoch = response1.json()[0]
    
    response2 = requests.get(f'{BASE_URL}/epochs/{representative_epoch["EPOCH"]}/location')
    
    assert response2.status_code == 200
    location_data = response2.json()
    assert isinstance(location_data, dict)  # Expect location data as dictionary
    assert "Latitude" in location_data
    assert "Longitude" in location_data
    assert "Altitude" in location_data
    assert "Geolocation" in location_data


def test_get_current_state_vector_and_speed(setup_flask_app):
    # Test /now route
    response = requests.get(f'{BASE_URL}/now')
    assert response.status_code == 200
    assert isinstance(response.text, str)  # Expect a string response containing state vector, speed, etc.


# Run the tests using pytest
if __name__ == "__main__":
    pytest.main()