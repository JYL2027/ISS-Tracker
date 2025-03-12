import pytest
import math
import json
from unittest import mock
import requests
import json
from iss_tracker import calc_closest_speed
from app import app, fetch_data, rd  # Assuming your app file is app.py

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

