"""Configuration and environment variable management for Weather MCP Server"""
import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# User Agent for API requests
USER_AGENT = os.getenv("NWS_USER_AGENT", "test@example.com")

# Weather.gov API Configuration
WEATHER_API_HOST = os.getenv("WEATHER_API_HOST", "api.weather.gov")
WEATHER_API_PORT = os.getenv("WEATHER_API_PORT", "443")
WEATHER_API_PROTOCOL = os.getenv("WEATHER_API_PROTOCOL", "https")
WEATHER_API_POINTS_PATH = os.getenv("WEATHER_API_POINTS_PATH", "/points")

# US Census API Configuration
CENSUS_API_HOST = os.getenv("CENSUS_API_HOST", "geocoding.geo.census.gov")
CENSUS_API_PORT = os.getenv("CENSUS_API_PORT", "443")
CENSUS_API_PROTOCOL = os.getenv("CENSUS_API_PROTOCOL", "https")
CENSUS_API_PATH = os.getenv("CENSUS_API_PATH", "/geocoder/locations/onelineaddress")

# Nominatim API Configuration
NOMINATIM_API_HOST = os.getenv("NOMINATIM_API_HOST", "nominatim.openstreetmap.org")
NOMINATIM_API_PORT = os.getenv("NOMINATIM_API_PORT", "443")
NOMINATIM_API_PROTOCOL = os.getenv("NOMINATIM_API_PROTOCOL", "https")
NOMINATIM_API_PATH = os.getenv("NOMINATIM_API_PATH", "/search")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

def setup_logging():
    """Configure application logging"""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    # Reduce noise from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('geopy').setLevel(logging.WARNING)

def build_api_url(host: str, port: str, protocol: str, path: str = "") -> str:
    """Build API URLs from components"""
    port_str = f":{port}" if port != "443" and port != "80" else ""
    return f"{protocol}://{host}{port_str}{path}"

def log_configuration():
    """Log configuration information"""
    logger.info(f"Weather MCP Server Configuration:")
    logger.info("API Configuration:")
    logger.info(f"   - Weather API: {WEATHER_API_PROTOCOL}://{WEATHER_API_HOST}:{WEATHER_API_PORT}")
    logger.info(f"   - Census API: {CENSUS_API_PROTOCOL}://{CENSUS_API_HOST}:{CENSUS_API_PORT}")
    logger.info(f"   - Nominatim API: {NOMINATIM_API_PROTOCOL}://{NOMINATIM_API_HOST}:{NOMINATIM_API_PORT}")
    logger.info(f"   - User Agent: {USER_AGENT}")
    logger.info(f"   - Log Level: {LOG_LEVEL}")
