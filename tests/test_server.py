import pytest
from server.app import get_weather

def test_get_weather_zip(monkeypatch):
    # simulate API responses
    class DummyResp:
        def __init__(self, json_data): 
            self._j = json_data
        def raise_for_status(self): 
            pass
        def json(self): 
            return self._j
            
    def mock_requests_get(url, headers=None, timeout=None):

        if "zippopotam" in url:
            response_data = {"places":[{"latitude":"38.0","longitude":"-77.0"}]}

            return DummyResp(response_data)
        elif "gridpoints" in url:  # This must come BEFORE the "points" check
            response_data = {"properties":{"periods":[{"name":"Today","shortForecast":"Sunny","temperature":70,"temperatureUnit":"F"}]}}

            return DummyResp(response_data)
        elif "points" in url and "api.weather.gov" in url:
            response_data = {"properties":{"forecast":"https://api.weather.gov/gridpoints/LWX/97,71/forecast"}}

            return DummyResp(response_data)  
        else:

            return DummyResp({"error": "Unknown URL pattern"})
    
    monkeypatch.setattr("server.app.requests.get", mock_requests_get)
    res = get_weather(zip_code="20500")
    assert "Sunny" in res.content[0].text

def test_get_weather_no_input():
    res = get_weather()
    assert "Error" in res.content[0].text

def test_get_weather_city(monkeypatch):
    # Mock geocoding and weather API responses
    class MockLocation:
        def __init__(self):
            self.latitude = 40.7128
            self.longitude = -74.0060
    
    class DummyResp:
        def __init__(self, json_data): 
            self._j = json_data
        def raise_for_status(self): 
            pass
        def json(self): 
            return self._j
    
    def mock_requests_get(url, headers=None, timeout=None):
  
        if "gridpoints" in url:  # This must come BEFORE the "points" check
            return DummyResp({"properties":{"periods":[{"name":"Tonight","shortForecast":"Clear","temperature":65,"temperatureUnit":"F"}]}})
        elif "points" in url and "api.weather.gov" in url:
            return DummyResp({"properties":{"forecast":"https://api.weather.gov/gridpoints/OKX/32,34/forecast"}})
        else:
            return DummyResp({"error": "Unknown URL pattern in city test"})
    
    # Mock geocoder
    class MockGeolocator:
        def geocode(self, city, timeout=None):
            return MockLocation()
    
    monkeypatch.setattr("server.app.requests.get", mock_requests_get)
    monkeypatch.setattr("server.app.Nominatim", lambda user_agent: MockGeolocator())
    
    res = get_weather(city="New York")
    assert "Clear" in res.content[0].text

def test_get_weather_invalid_zip(monkeypatch):
    # Mock failed zip code lookup
    class DummyResp:
        def raise_for_status(self):
            from requests.exceptions import HTTPError
            raise HTTPError("404 Client Error")
        def json(self):
            return {}
    
    monkeypatch.setattr("server.app.requests.get", lambda url, headers=None, timeout=None: DummyResp())
    res = get_weather(zip_code="00000")
    assert "Error" in res.content[0].text

def test_get_weather_city_not_found(monkeypatch):
    # Mock geocoder returning None
    class MockGeolocator:
        def geocode(self, city, timeout=None):
            return None
    
    monkeypatch.setattr("server.app.Nominatim", lambda user_agent: MockGeolocator())
    res = get_weather(city="InvalidCity12345")
    assert "Error" in res.content[0].text
