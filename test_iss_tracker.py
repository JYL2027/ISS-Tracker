import pytest
import math
import json
from unittest import mock
import requests
import json
from iss_tracker import calc_closest_speed

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

import pytest
from flask import Flask, jsonify

# Create a minimal Flask app for testing purposes
app = Flask(__name__)

# Sample route definitions (replace with actual route logic in your app)
@app.route('/epochs', methods=['GET'])
def get_epochs():
    # Sample response for testing
    return jsonify([{'epoch_time': 1234567890, 'id': 1}, {'epoch_time': 1234567891, 'id': 2}])

@app.route('/epochs/<int:epoch_id>', methods=['GET'])
def get_specific_epoch(epoch_id):
    # Sample response for testing
    return jsonify({'epoch_time': 1234567890, 'id': epoch_id})

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

def test_epochs_route(client):
    response = client.get('/epochs')
    
    # Check that the status code is 200 (OK)
    assert response.status_code == 200
    
    # Check that the response is a list
    assert isinstance(response.json, list)
    
    # Optionally, check that the list is not empty
    assert len(response.json) > 0

def test_specific_epoch_route(client):
    # Assuming the first item in the epochs list is a representative epoch
    response1 = client.get('/epochs')
    a_representative_epoch = response1.json[0]['id']  # Use 'id' for the representative epoch
    
    # Use the representative epoch to make a request for the specific epoch
    response2 = client.get(f'/epochs/{a_representative_epoch}')
    
    # Check that the status code is 200 (OK)
    assert response2.status_code == 200
    
    # Check that the response is a dictionary
    assert isinstance(response2.json, dict)
    
    # Optionally, verify that specific data from the dictionary is correct
    assert 'id' in response2.json
    assert 'epoch_time' in response2.json

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

