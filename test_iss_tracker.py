import pytest
import math
import json
from unittest import mock
import requests
import json
from iss_tracker import calc_closest_speed, fetch_data_from_redis
from app import app, fetch_data, rd  # Assuming your app file is app.py

@pytest.fixture
def mock_redis():
    with mock.patch('app.rd') as mock_rd:
        yield mock_rd

@pytest.fixture
def mock_requests():
    with mock.patch('app.requests.get') as mock_get:
        yield mock_get

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_redis():
    """Fixture to set up Redis for testing"""
    rd.flushdb()  # Clear Redis DB before each test
    yield rd  # Provide the Redis instance to the test
    rd.flushdb()  # Clean up after test

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

def test_fetch_data_from_redis(mock_redis):
    # Prepare mock data
    mock_redis.keys.return_value = ['12345']
    mock_redis.get.return_value = json.dumps({
    "EPOCH": "2025-001T12:00:00.000Z",
    "X": {"#text": "7000"},
    "Y": {"#text": "5000"},
    "Z": {"#text": "4000"},
    "X_DOT": {"#text": "0.1"},
    "Y_DOT": {"#text": "0.2"},
    "Z_DOT": {"#text": "0.3"}
})

    # Call the function
    data = fetch_data_from_redis()

    # Check if the data returned is a list and has one entry
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["EPOCH"] == "2025-001T12:00:00.000Z"

def test_get_epochs(client, mock_redis):
    # Mock the data in Redis
    mock_redis.keys.return_value = ['2025-001T12:00:00.000Z']
    mock_redis.get.return_value = json.dumps({
        "EPOCH": "2025-001T12:00:00.000Z",
        "X": {"#text": "7000"},
        "Y": {"#text": "5000"},
        "Z": {"#text": "4000"},
        "X_DOT": {"#text": "0.1"},
        "Y_DOT": {"#text": "0.2"},
        "Z_DOT": {"#text": "0.3"}
    })

    # Call the `/epochs` route
    response = client.get('/epochs')

    assert response.status_code == 200
    assert b"2025-001T12:00:00.000Z" in response.data

def test_get_epoch_data(client, mock_redis):
    # Mock Redis data
    mock_redis.get.return_value = json.dumps({
        "EPOCH": "2025-001T12:00:00.000Z",
        "X": {"#text": "7000"},
        "Y": {"#text": "5000"},
        "Z": {"#text": "4000"},
        "X_DOT": {"#text": "0.1"},
        "Y_DOT": {"#text": "0.2"},
        "Z_DOT": {"#text": "0.3"}
    })

    # Call the `/epochs/<epoch>` route
    response = client.get('/epochs/2025-001T12:00:00.000Z')

    assert response.status_code == 200
    assert b"Epoch: 2025-001T12:00:00.000Z" in response.data

def test_get_location():
    """Test /location route for valid latitude and longitude"""
    with app.test_client() as client:
        # Valid latitude and longitude for a known location (e.g., New York City)
        lat = 40.7128
        lon = -74.0060
        response = client.get(f'/location?lat={lat}&lon={lon}')
        
        assert response.status_code == 200, "Failed to fetch location"
        data = response.get_json()
        assert "address" in data, "Address key not found in response"
        assert "New York" in data["address"], "Location address mismatch"



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

def test_get_location_exceptions():
    """Test /location route with invalid latitude and longitude"""
    with app.test_client() as client:
        # Invalid latitude and longitude
        lat = 999.999
        lon = 999.999
        response = client.get(f'/location?lat={lat}&lon={lon}')
        
        assert response.status_code == 404, "Location should not be found"
        data = response.get_json()
        assert "Error" in data, "Expected error message"
