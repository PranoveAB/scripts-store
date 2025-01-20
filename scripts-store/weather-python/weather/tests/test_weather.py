# tests/test_weather.py
import pytest
from unittest.mock import patch, Mock
import pandas as pd
import matplotlib.pyplot as plt
from main import get_weather, create_plot  # This is the correct import
import os

@pytest.fixture
def mock_weather_data():
    return [
        {
            'city': 'Nairobi',
            'temperature': '25°C',
            'description': 'Sunny',
            'time': '2025-01-11 12:00:00'
        }
    ]

def test_get_weather():
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'temperature': '25°C',
        'description': 'Sunny'
    }
    
    with patch('requests.get', return_value=mock_response):
        result = get_weather()
        assert isinstance(result, list)
        assert len(result) > 0
        assert 'city' in result[0]
        assert 'temperature' in result[0]

def test_create_plot(mock_weather_data):
    with patch('matplotlib.pyplot.savefig'), \
         patch('os.makedirs'):  # Mock directory creation
        create_plot(mock_weather_data)
        # If we get here without errors, test passes
        assert True