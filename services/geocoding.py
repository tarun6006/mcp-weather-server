"""Geocoding services for ZIP code and city resolution"""
import requests
import logging
from typing import Tuple, Optional
from geopy.geocoders import Nominatim
from config.settings import (
    CENSUS_API_HOST, CENSUS_API_PORT, CENSUS_API_PROTOCOL, CENSUS_API_PATH,
    NOMINATIM_API_HOST, NOMINATIM_API_PORT, NOMINATIM_API_PROTOCOL,
    build_api_url
)

logger = logging.getLogger(__name__)

class GeocodingService:
    """Service for resolving geographic locations to coordinates"""
    
    def __init__(self):
        self.census_url = build_api_url(CENSUS_API_HOST, CENSUS_API_PORT, CENSUS_API_PROTOCOL, CENSUS_API_PATH)
        self.nominatim_url = build_api_url(NOMINATIM_API_HOST, NOMINATIM_API_PORT, NOMINATIM_API_PROTOCOL)
    
    def resolve_zip_code(self, zip_code: str) -> Tuple[Optional[float], Optional[float]]:
        """Resolve ZIP code to coordinates using Census API and Nominatim fallback"""
        
        # Try US Census API first
        lat, lon = self._try_census_api(zip_code)
        if lat is not None and lon is not None:
            return lat, lon
        
        # Try Nominatim as fallback
        lat, lon = self._try_nominatim_zip(zip_code)
        if lat is not None and lon is not None:
            return lat, lon
        
        logger.error(f"Both Census and Nominatim failed for ZIP code {zip_code}")
        return None, None
    
    def resolve_city(self, city: str) -> Tuple[Optional[float], Optional[float]]:
        """Resolve city name to coordinates using Nominatim"""
        try:
            logger.debug(f"Resolving city: {city}")
            geolocator = Nominatim(user_agent="weather-mcp")
            location = geolocator.geocode(city, timeout=5)
            
            if not location:
                logger.error(f"Location not found for city: {city}")
                return None, None
            
            lat, lon = location.latitude, location.longitude
            logger.debug(f"City {city} resolved to coordinates: ({lat}, {lon})")
            return lat, lon
            
        except Exception as e:
            logger.error(f"Error resolving city {city}: {e}")
            return None, None
    
    def _try_census_api(self, zip_code: str) -> Tuple[Optional[float], Optional[float]]:
        """Try to resolve ZIP code using US Census API"""
        try:
            params = {
                "address": zip_code,
                "benchmark": "2020",
                "format": "json"
            }
            
            response = requests.get(self.census_url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get('result', {}).get('addressMatches'):
                    match = data['result']['addressMatches'][0]
                    coords = match['coordinates']
                    lat, lon = float(coords['y']), float(coords['x'])
                    logger.info(f"Census API resolved {zip_code}: ({lat}, {lon})")
                    return lat, lon
        except Exception as e:
            logger.warning(f"Census API failed for {zip_code}: {e}")
        
        return None, None
    
    def _try_nominatim_zip(self, zip_code: str) -> Tuple[Optional[float], Optional[float]]:
        """Try to resolve ZIP code using Nominatim API"""
        try:
            domain = self.nominatim_url.replace("https://", "").replace("http://", "")
            geolocator = Nominatim(user_agent="weather-mcp-improved", domain=domain)
            
            formats = [
                f"postcode:{zip_code}, country:US",
                f"{zip_code}, United States",
                f"{zip_code}, USA",
                f"{zip_code}, US"
            ]
            
            for zip_format in formats:
                try:
                    location = geolocator.geocode(zip_format, country_codes='us', timeout=15)
                    if location:
                        logger.info(f"Nominatim resolved {zip_code}: {location.address}")
                        return location.latitude, location.longitude
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Nominatim failed for {zip_code}: {e}")
        
        return None, None
