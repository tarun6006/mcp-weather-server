"""Weather service for fetching weather data from NWS API"""
import requests
import logging
from typing import Dict, Any, Optional
from mcp_utils.schema import CallToolResult, TextContent
from services.geocoding import GeocodingService
from config.settings import (
    WEATHER_API_HOST, WEATHER_API_PORT, WEATHER_API_PROTOCOL, 
    WEATHER_API_POINTS_PATH, USER_AGENT, build_api_url
)

logger = logging.getLogger(__name__)

class WeatherService:
    """Service for fetching weather information"""
    
    def __init__(self):
        self.geocoding = GeocodingService()
        self.weather_base_url = build_api_url(WEATHER_API_HOST, WEATHER_API_PORT, WEATHER_API_PROTOCOL)
        self.headers = {"User-Agent": USER_AGENT}
    
    def get_weather(self, city: str = None, zip_code: str = None) -> CallToolResult:
        """Get weather information for a city or ZIP code"""
        try:
            logger.info(f"Weather request received - city: {city}, zip_code: {zip_code}")
            
            # Resolve location to coordinates
            lat, lon = self._resolve_location(city, zip_code)
            if lat is None or lon is None:
                error_msg = f"Could not resolve location: city={city}, zip_code={zip_code}"
                logger.error(error_msg)
                return CallToolResult(content=[TextContent(type='text', text=f"Error: {error_msg}")])
            
            # Get weather forecast
            forecast_text = self._fetch_weather_forecast(lat, lon)
            if forecast_text:
                logger.info(f"Weather forecast retrieved successfully: {forecast_text}")
                return CallToolResult(content=[TextContent(type='text', text=forecast_text)])
            else:
                error_msg = "Failed to fetch weather forecast"
                logger.error(error_msg)
                return CallToolResult(content=[TextContent(type='text', text=f"Error: {error_msg}")])
            
        except Exception as e:
            error_msg = f"Weather service error: {str(e)}"
            logger.error(error_msg)
            return CallToolResult(content=[TextContent(type='text', text=f"Error: {error_msg}")])
    
    def _resolve_location(self, city: str = None, zip_code: str = None) -> tuple[Optional[float], Optional[float]]:
        """Resolve city or ZIP code to coordinates"""
        if zip_code:
            logger.debug(f"Resolving ZIP code: {zip_code}")
            return self.geocoding.resolve_zip_code(zip_code)
        elif city:
            logger.debug(f"Resolving city: {city}")
            return self.geocoding.resolve_city(city)
        else:
            logger.error("No city or zip_code provided")
            raise ValueError("Provide city or zip_code")
    
    def _fetch_weather_forecast(self, lat: float, lon: float) -> Optional[str]:
        """Fetch weather forecast from NWS API"""
        try:
            # Get forecast URL from NWS points API
            points_url = f"{self.weather_base_url}{WEATHER_API_POINTS_PATH}/{lat},{lon}"
            logger.debug(f"Requesting weather grid points from: {points_url}")
            
            point_response = requests.get(points_url, headers=self.headers, timeout=10)
            point_response.raise_for_status()
            forecast_url = point_response.json()['properties']['forecast']
            logger.debug(f"Forecast URL obtained: {forecast_url}")
            
            # Get actual forecast data
            logger.debug("Requesting weather forecast data")
            forecast_response = requests.get(forecast_url, headers=self.headers, timeout=10)
            forecast_response.raise_for_status()
            data = forecast_response.json()['properties']['periods'][0]
            
            # Format forecast text
            forecast_text = f"{data['name']}: {data['shortForecast']} at {data['temperature']}°{data['temperatureUnit']}"
            return forecast_text
            
        except Exception as e:
            logger.error(f"Error fetching weather forecast: {e}")
            return None
