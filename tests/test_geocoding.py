"""
Black box tests for geocoding service
Tests location resolution without knowing internal implementation
"""
import pytest
from unittest.mock import patch, Mock
import requests
from geopy.geocoders import Nominatim
from services.geocoding import GeocodingService

class TestGeocodingService:
    """Test geocoding service functionality"""
    
    def setup_method(self):
        """Setup geocoding service for each test"""
        self.geocoding = GeocodingService()
    
    # ZIP Code Resolution Tests
    @patch('services.geocoding.requests.get')
    def test_resolve_zip_code_census_success(self, mock_requests_get):
        """Test successful ZIP code resolution using Census API"""
        # Mock successful Census API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': {
                'addressMatches': [{
                    'coordinates': {
                        'x': -74.0060,
                        'y': 40.7128
                    }
                }]
            }
        }
        mock_requests_get.return_value = mock_response
        
        lat, lon = self.geocoding.resolve_zip_code("10001")
        
        assert lat == 40.7128
        assert lon == -74.0060
        mock_requests_get.assert_called_once()
    
    @patch('services.geocoding.requests.get')
    @patch('geopy.geocoders.Nominatim.geocode')
    def test_resolve_zip_code_nominatim_fallback(self, mock_nominatim_geocode, mock_requests_get):
        """Test ZIP code resolution falling back to Nominatim"""
        # Mock Census API failure
        mock_requests_get.side_effect = Exception("Census API failed")
        
        # Mock successful Nominatim response
        mock_location = Mock()
        mock_location.latitude = 40.7589
        mock_location.longitude = -73.9851
        mock_location.address = "New York, NY, USA"
        mock_nominatim_geocode.return_value = mock_location
        
        lat, lon = self.geocoding.resolve_zip_code("10001")
        
        assert lat == 40.7589
        assert lon == -73.9851
        mock_nominatim_geocode.assert_called()
    
    @patch('services.geocoding.requests.get')
    @patch('geopy.geocoders.Nominatim.geocode')
    def test_resolve_zip_code_both_fail(self, mock_nominatim_geocode, mock_requests_get):
        """Test ZIP code resolution when both APIs fail"""
        # Mock both API failures
        mock_requests_get.side_effect = Exception("Census API failed")
        mock_nominatim_geocode.return_value = None
        
        lat, lon = self.geocoding.resolve_zip_code("00000")
        
        assert lat is None
        assert lon is None
    
    @patch('services.geocoding.requests.get')
    def test_resolve_zip_code_census_no_matches(self, mock_requests_get):
        """Test ZIP code resolution when Census API returns no matches"""
        # Mock Census API with no matches
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': {
                'addressMatches': []
            }
        }
        mock_requests_get.return_value = mock_response
        
        with patch('geopy.geocoders.Nominatim.geocode') as mock_nominatim:
            mock_nominatim.return_value = None
            
            lat, lon = self.geocoding.resolve_zip_code("00000")
            
            assert lat is None
            assert lon is None
    
    @patch('services.geocoding.requests.get')
    def test_resolve_zip_code_census_malformed_response(self, mock_requests_get):
        """Test ZIP code resolution with malformed Census API response"""
        # Mock malformed Census API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"unexpected": "format"}
        mock_requests_get.return_value = mock_response
        
        with patch('geopy.geocoders.Nominatim.geocode') as mock_nominatim:
            mock_nominatim.return_value = None
            
            lat, lon = self.geocoding.resolve_zip_code("10001")
            
            assert lat is None
            assert lon is None
    
    @patch('services.geocoding.requests.get')
    @patch('geopy.geocoders.Nominatim.geocode')
    def test_resolve_zip_code_nominatim_multiple_formats(self, mock_nominatim_geocode, mock_requests_get):
        """Test that Nominatim tries multiple ZIP code formats"""
        # Mock Census API failure
        mock_requests_get.side_effect = Exception("Census API failed")
        
        # Mock Nominatim to succeed on second format
        mock_location = Mock()
        mock_location.latitude = 40.7128
        mock_location.longitude = -74.0060
        mock_location.address = "New York, NY, USA"
        
        mock_nominatim_geocode.side_effect = [None, mock_location]  # Fail first, succeed second
        
        lat, lon = self.geocoding.resolve_zip_code("10001")
        
        assert lat == 40.7128
        assert lon == -74.0060
        assert mock_nominatim_geocode.call_count >= 2
    
    # City Resolution Tests
    @patch('geopy.geocoders.Nominatim.geocode')
    def test_resolve_city_success(self, mock_geocode):
        """Test successful city resolution"""
        mock_location = Mock()
        mock_location.latitude = 42.3601
        mock_location.longitude = -71.0589
        mock_geocode.return_value = mock_location
        
        lat, lon = self.geocoding.resolve_city("Boston")
        
        assert lat == 42.3601
        assert lon == -71.0589
        mock_geocode.assert_called_once_with("Boston", timeout=5)
    
    @patch('geopy.geocoders.Nominatim.geocode')
    def test_resolve_city_not_found(self, mock_geocode):
        """Test city resolution when city is not found"""
        mock_geocode.return_value = None
        
        lat, lon = self.geocoding.resolve_city("NonexistentCity")
        
        assert lat is None
        assert lon is None
    
    @patch('geopy.geocoders.Nominatim.geocode')
    def test_resolve_city_exception(self, mock_geocode):
        """Test city resolution with exception"""
        mock_geocode.side_effect = Exception("Geocoding failed")
        
        lat, lon = self.geocoding.resolve_city("Boston")
        
        assert lat is None
        assert lon is None
    
    @patch('geopy.geocoders.Nominatim.geocode')
    def test_resolve_city_timeout(self, mock_geocode):
        """Test city resolution with timeout"""
        mock_geocode.side_effect = Exception("Timeout")
        
        lat, lon = self.geocoding.resolve_city("Boston")
        
        assert lat is None
        assert lon is None
    
    # Edge Cases and Error Handling
    def test_resolve_empty_zip_code(self):
        """Test resolving empty ZIP code"""
        lat, lon = self.geocoding.resolve_zip_code("")
        
        assert lat is None
        assert lon is None
    
    def test_resolve_empty_city(self):
        """Test resolving empty city name"""
        lat, lon = self.geocoding.resolve_city("")
        
        assert lat is None
        assert lon is None
    
    def test_resolve_none_zip_code(self):
        """Test resolving None ZIP code"""
        lat, lon = self.geocoding.resolve_zip_code(None)
        
        # Should handle None gracefully
        assert lat is None
        assert lon is None
    
    def test_resolve_none_city(self):
        """Test resolving None city"""
        lat, lon = self.geocoding.resolve_city(None)
        
        # Should handle None gracefully
        assert lat is None
        assert lon is None
    
    @patch('services.geocoding.requests.get')
    def test_resolve_zip_code_http_error(self, mock_requests_get):
        """Test ZIP code resolution with HTTP error"""
        # Mock HTTP error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_requests_get.return_value = mock_response
        
        with patch('geopy.geocoders.Nominatim.geocode') as mock_nominatim:
            mock_nominatim.return_value = None
            
            lat, lon = self.geocoding.resolve_zip_code("10001")
            
            assert lat is None
            assert lon is None
    
    @patch('services.geocoding.requests.get')
    def test_resolve_zip_code_json_decode_error(self, mock_requests_get):
        """Test ZIP code resolution with JSON decode error"""
        # Mock response that can't be decoded as JSON
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_requests_get.return_value = mock_response
        
        with patch('geopy.geocoders.Nominatim.geocode') as mock_nominatim:
            mock_nominatim.return_value = None
            
            lat, lon = self.geocoding.resolve_zip_code("10001")
            
            assert lat is None
            assert lon is None
    
    # Integration-like Tests
    @patch('services.geocoding.requests.get')
    @patch('geopy.geocoders.Nominatim.geocode')
    def test_resolve_zip_code_census_success_coordinates_conversion(self, mock_nominatim, mock_requests_get):
        """Test that Census API coordinates are properly converted"""
        # Mock Census API with string coordinates (as they sometimes return)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': {
                'addressMatches': [{
                    'coordinates': {
                        'x': '-74.0060',  # String instead of float
                        'y': '40.7128'
                    }
                }]
            }
        }
        mock_requests_get.return_value = mock_response
        
        lat, lon = self.geocoding.resolve_zip_code("10001")
        
        assert lat == 40.7128
        assert lon == -74.0060
        # Should not fall back to Nominatim
        mock_nominatim.assert_not_called()
    
    def test_api_url_construction(self):
        """Test that API URLs are constructed correctly"""
        # This tests the initialization and URL building
        assert self.geocoding.census_url.startswith("https://")
        assert "geocoding.geo.census.gov" in self.geocoding.census_url
        assert self.geocoding.nominatim_url.startswith("https://")
        assert "nominatim.openstreetmap.org" in self.geocoding.nominatim_url
    
    @patch('geopy.geocoders.Nominatim.geocode')
    def test_resolve_city_with_special_characters(self, mock_geocode):
        """Test city resolution with special characters"""
        mock_location = Mock()
        mock_location.latitude = 40.7128
        mock_location.longitude = -74.0060
        mock_geocode.return_value = mock_location
        
        lat, lon = self.geocoding.resolve_city("New York City")
        
        assert lat == 40.7128
        assert lon == -74.0060
        mock_geocode.assert_called_once_with("New York City", timeout=5)
