"""
Black box tests for weather service
Tests weather data retrieval without knowing internal implementation
"""
import pytest
from unittest.mock import patch, Mock, MagicMock
from services.weather import WeatherService
from mcp_utils.schema import CallToolResult, TextContent

class TestWeatherService:
    """Test weather service functionality"""
    
    def setup_method(self):
        """Setup weather service for each test"""
        self.weather_service = WeatherService()
    
    @patch('services.weather.requests.get')
    def test_get_weather_by_city_success(self, mock_requests_get):
        """Test successful weather retrieval by city"""
        # Mock geocoding
        with patch.object(self.weather_service.geocoding, 'resolve_city') as mock_resolve:
            mock_resolve.return_value = (40.7128, -74.0060)  # NYC coordinates
            
            # Mock weather API responses
            mock_points_response = Mock()
            mock_points_response.raise_for_status.return_value = None
            mock_points_response.json.return_value = {
                'properties': {'forecast': 'https://api.weather.gov/forecast/123'}
            }
            
            mock_forecast_response = Mock()
            mock_forecast_response.raise_for_status.return_value = None
            mock_forecast_response.json.return_value = {
                'properties': {
                    'periods': [{
                        'name': 'Today',
                        'shortForecast': 'Sunny',
                        'temperature': 75,
                        'temperatureUnit': 'F'
                    }]
                }
            }
            
            mock_requests_get.side_effect = [mock_points_response, mock_forecast_response]
            
            result = self.weather_service.get_weather(city="New York")
            
            assert isinstance(result, CallToolResult)
            assert len(result.content) == 1
            assert isinstance(result.content[0], TextContent)
            assert "Today: Sunny at 75°F" in result.content[0].text
    
    @patch('services.weather.requests.get')
    def test_get_weather_by_zip_code_success(self, mock_requests_get):
        """Test successful weather retrieval by ZIP code"""
        # Mock geocoding
        with patch.object(self.weather_service.geocoding, 'resolve_zip_code') as mock_resolve:
            mock_resolve.return_value = (40.7128, -74.0060)  # NYC coordinates
            
            # Mock weather API responses
            mock_points_response = Mock()
            mock_points_response.raise_for_status.return_value = None
            mock_points_response.json.return_value = {
                'properties': {'forecast': 'https://api.weather.gov/forecast/123'}
            }
            
            mock_forecast_response = Mock()
            mock_forecast_response.raise_for_status.return_value = None
            mock_forecast_response.json.return_value = {
                'properties': {
                    'periods': [{
                        'name': 'Tonight',
                        'shortForecast': 'Clear',
                        'temperature': 65,
                        'temperatureUnit': 'F'
                    }]
                }
            }
            
            mock_requests_get.side_effect = [mock_points_response, mock_forecast_response]
            
            result = self.weather_service.get_weather(zip_code="10001")
            
            assert isinstance(result, CallToolResult)
            assert "Tonight: Clear at 65°F" in result.content[0].text
    
    def test_get_weather_no_location_provided(self):
        """Test weather retrieval with no location provided"""
        result = self.weather_service.get_weather()
        
        assert isinstance(result, CallToolResult)
        assert "Error:" in result.content[0].text
        assert "city or zip_code" in result.content[0].text
    
    def test_get_weather_city_not_found(self):
        """Test weather retrieval with city that cannot be resolved"""
        with patch.object(self.weather_service.geocoding, 'resolve_city') as mock_resolve:
            mock_resolve.return_value = (None, None)
            
            result = self.weather_service.get_weather(city="NonexistentCity")
            
            assert isinstance(result, CallToolResult)
            assert "Error:" in result.content[0].text
            assert "Could not resolve location" in result.content[0].text
    
    def test_get_weather_zip_code_not_found(self):
        """Test weather retrieval with ZIP code that cannot be resolved"""
        with patch.object(self.weather_service.geocoding, 'resolve_zip_code') as mock_resolve:
            mock_resolve.return_value = (None, None)
            
            result = self.weather_service.get_weather(zip_code="00000")
            
            assert isinstance(result, CallToolResult)
            assert "Error:" in result.content[0].text
            assert "Could not resolve location" in result.content[0].text
    
    @patch('services.weather.requests.get')
    def test_get_weather_api_error(self, mock_requests_get):
        """Test weather retrieval with API error"""
        with patch.object(self.weather_service.geocoding, 'resolve_city') as mock_resolve:
            mock_resolve.return_value = (40.7128, -74.0060)
            
            # Mock API error
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = Exception("API Error")
            mock_requests_get.return_value = mock_response
            
            result = self.weather_service.get_weather(city="New York")
            
            assert isinstance(result, CallToolResult)
            assert "Error:" in result.content[0].text
    
    @patch('services.weather.requests.get')
    def test_get_weather_forecast_fetch_failure(self, mock_requests_get):
        """Test weather retrieval when forecast fetch fails"""
        with patch.object(self.weather_service.geocoding, 'resolve_city') as mock_resolve:
            mock_resolve.return_value = (40.7128, -74.0060)
            
            # Mock successful points request but failed forecast
            mock_points_response = Mock()
            mock_points_response.raise_for_status.return_value = None
            mock_points_response.json.return_value = {
                'properties': {'forecast': 'https://api.weather.gov/forecast/123'}
            }
            
            mock_forecast_response = Mock()
            mock_forecast_response.raise_for_status.side_effect = Exception("Forecast Error")
            
            mock_requests_get.side_effect = [mock_points_response, mock_forecast_response]
            
            result = self.weather_service.get_weather(city="New York")
            
            assert isinstance(result, CallToolResult)
            assert "Error:" in result.content[0].text
    
    def test_get_weather_both_city_and_zip_provided(self):
        """Test weather retrieval with both city and ZIP code (should prefer ZIP)"""
        with patch.object(self.weather_service.geocoding, 'resolve_zip_code') as mock_resolve_zip:
            mock_resolve_zip.return_value = (40.7128, -74.0060)
            
            with patch('services.weather.requests.get') as mock_requests_get:
                # Mock successful API responses
                mock_points_response = Mock()
                mock_points_response.raise_for_status.return_value = None
                mock_points_response.json.return_value = {
                    'properties': {'forecast': 'https://api.weather.gov/forecast/123'}
                }
                
                mock_forecast_response = Mock()
                mock_forecast_response.raise_for_status.return_value = None
                mock_forecast_response.json.return_value = {
                    'properties': {
                        'periods': [{
                            'name': 'Today',
                            'shortForecast': 'Sunny',
                            'temperature': 75,
                            'temperatureUnit': 'F'
                        }]
                    }
                }
                
                mock_requests_get.side_effect = [mock_points_response, mock_forecast_response]
                
                result = self.weather_service.get_weather(city="Boston", zip_code="10001")
                
                # Should use ZIP code resolution, not city
                mock_resolve_zip.assert_called_once_with("10001")
                assert isinstance(result, CallToolResult)
    
    def test_get_weather_exception_handling(self):
        """Test weather retrieval with unexpected exception"""
        with patch.object(self.weather_service.geocoding, 'resolve_city') as mock_resolve:
            mock_resolve.side_effect = Exception("Unexpected error")
            
            result = self.weather_service.get_weather(city="New York")
            
            assert isinstance(result, CallToolResult)
            assert "Error:" in result.content[0].text
            assert "Weather service error" in result.content[0].text
    
    @patch('services.weather.requests.get')
    def test_get_weather_malformed_api_response(self, mock_requests_get):
        """Test weather retrieval with malformed API response"""
        with patch.object(self.weather_service.geocoding, 'resolve_city') as mock_resolve:
            mock_resolve.return_value = (40.7128, -74.0060)
            
            # Mock malformed response
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {"unexpected": "format"}
            mock_requests_get.return_value = mock_response
            
            result = self.weather_service.get_weather(city="New York")
            
            assert isinstance(result, CallToolResult)
            assert "Error:" in result.content[0].text
    
    @patch('services.weather.requests.get')
    def test_get_weather_timeout_handling(self, mock_requests_get):
        """Test weather retrieval with request timeout"""
        with patch.object(self.weather_service.geocoding, 'resolve_city') as mock_resolve:
            mock_resolve.return_value = (40.7128, -74.0060)
            
            # Mock timeout
            mock_requests_get.side_effect = Exception("Request timeout")
            
            result = self.weather_service.get_weather(city="New York")
            
            assert isinstance(result, CallToolResult)
            assert "Error:" in result.content[0].text
