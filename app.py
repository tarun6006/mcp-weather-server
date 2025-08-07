import os
import requests
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from queue import Queue
import mcp_utils
from mcp_utils.core import MCPServer
from mcp_utils.schema import GetPromptResult, Message, TextContent, CallToolResult
from geopy.geocoders import Nominatim
from requests.exceptions import HTTPError, RequestException

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Reduce noise from external libraries
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('geopy').setLevel(logging.WARNING)

load_dotenv()

USER_AGENT = os.getenv("NWS_USER_AGENT", "test@example.com")

WEATHER_API_HOST = os.getenv("WEATHER_API_HOST", "api.weather.gov")
WEATHER_API_PORT = os.getenv("WEATHER_API_PORT", "443")
WEATHER_API_PROTOCOL = os.getenv("WEATHER_API_PROTOCOL", "https")
WEATHER_API_POINTS_PATH = os.getenv("WEATHER_API_POINTS_PATH", "/points")

CENSUS_API_HOST = os.getenv("CENSUS_API_HOST", "geocoding.geo.census.gov")
CENSUS_API_PORT = os.getenv("CENSUS_API_PORT", "443")
CENSUS_API_PROTOCOL = os.getenv("CENSUS_API_PROTOCOL", "https")
CENSUS_API_PATH = os.getenv("CENSUS_API_PATH", "/geocoder/locations/onelineaddress")

NOMINATIM_API_HOST = os.getenv("NOMINATIM_API_HOST", "nominatim.openstreetmap.org")
NOMINATIM_API_PORT = os.getenv("NOMINATIM_API_PORT", "443")
NOMINATIM_API_PROTOCOL = os.getenv("NOMINATIM_API_PROTOCOL", "https")
NOMINATIM_API_PATH = os.getenv("NOMINATIM_API_PATH", "/search")

app = Flask(__name__)
response_queue = Queue()

try:
    mcp = MCPServer("weather-server", "1.0", response_queue)
    logger.info("MCPServer initialized with response_queue")
except TypeError as e:
    logger.warning(f"First initialization failed: {e}")
    try:
        mcp = MCPServer("weather-server", "1.0")
        if hasattr(mcp, 'response_queue'):
            mcp.response_queue = response_queue
        logger.info("MCPServer initialized without response_queue parameter")
    except Exception as e2:
        logger.warning(f"Second initialization failed: {e2}")
        mcp = MCPServer(name="weather-server", version="1.0")
        if hasattr(mcp, 'response_queue'):
            mcp.response_queue = response_queue
        logger.info("MCPServer initialized with keyword arguments")


def build_api_url(host, port, protocol, path=""):
    """Build API URLs from components"""
    port_str = f":{port}" if port != "443" and port != "80" else ""
    return f"{protocol}://{host}{port_str}{path}"

def resolve_zip_code_improved(zip_code):
    """Resolve ZIP code to coordinates using Census API and Nominatim fallback"""
    
    # Try US Census API first
    try:
        census_url = build_api_url(CENSUS_API_HOST, CENSUS_API_PORT, CENSUS_API_PROTOCOL, CENSUS_API_PATH)
        params = {
            "address": zip_code,
            "benchmark": "2020",
            "format": "json"
        }
        
        resp = requests.get(census_url, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('result', {}).get('addressMatches'):
                match = data['result']['addressMatches'][0]
                coords = match['coordinates']
                lat, lon = float(coords['y']), float(coords['x'])
                logger.info(f"Census API resolved {zip_code}: ({lat}, {lon})")
                return lat, lon
    except Exception as e:
        logger.warning(f"Census API failed for {zip_code}: {e}")
    
    # Try Nominatim as fallback
    try:
        nominatim_url = build_api_url(NOMINATIM_API_HOST, NOMINATIM_API_PORT, NOMINATIM_API_PROTOCOL)
        geolocator = Nominatim(user_agent="weather-mcp-improved", domain=nominatim_url.replace("https://", "").replace("http://", ""))
        
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
    
    logger.error(f"Both Census and Nominatim failed for ZIP code {zip_code}")
    return None, None


@mcp.tool()
def get_weather(city: str = None, zip_code: str = None) -> CallToolResult:
    try:
        logger.info(f"Weather request received - city: {city}, zip_code: {zip_code}")
        
        if zip_code:
            logger.debug(f"Resolving ZIP code: {zip_code}")
            lat, lon = resolve_zip_code_improved(zip_code)
            if lat is None or lon is None:
                logger.error(f"Could not resolve ZIP code {zip_code}")
                raise ValueError(f"Could not resolve ZIP code {zip_code}")
        elif city:
            logger.debug(f"Resolving city: {city}")
            geolocator = Nominatim(user_agent="weather-mcp")
            loc = geolocator.geocode(city, timeout=5)
            if not loc:
                logger.error(f"Location not found for city: {city}")
                raise ValueError("Location not found")
            lat, lon = loc.latitude, loc.longitude
            logger.debug(f"City {city} resolved to coordinates: ({lat}, {lon})")
        else:
            logger.error("No city or zip_code provided")
            raise ValueError("Provide city or zip_code")

        headers = {"User-Agent": USER_AGENT}
        weather_base_url = build_api_url(WEATHER_API_HOST, WEATHER_API_PORT, WEATHER_API_PROTOCOL)
        
        points_url = f"{weather_base_url}{WEATHER_API_POINTS_PATH}/{lat},{lon}"
        logger.debug(f"Requesting weather grid points from: {points_url}")
        
        point_resp = requests.get(points_url, headers=headers, timeout=10)
        point_resp.raise_for_status()
        forecast_url = point_resp.json()['properties']['forecast']
        logger.debug(f"Forecast URL obtained: {forecast_url}")

        logger.debug("Requesting weather forecast data")
        forecast_resp = requests.get(forecast_url, headers=headers, timeout=10)
        forecast_resp.raise_for_status()
        data = forecast_resp.json()['properties']['periods'][0]

        forecast_text = f"{data['name']}: {data['shortForecast']} at {data['temperature']}°{data['temperatureUnit']}"
        logger.info(f"Weather forecast retrieved successfully: {forecast_text}")
        return CallToolResult(content=[TextContent(type='text', text=forecast_text)])

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.error(f"Weather request failed: {error_msg}")
        return CallToolResult(content=[TextContent(type='text', text=error_msg)])


@app.route("/mcp", methods=["POST"])
def handle_mcp():
    body = request.get_json()
    logger.debug(f"MCP request received: {body}")
    
    try:
        response = mcp.handle_message(body)
        
        if hasattr(response, 'model_dump'):
            response_data = response.model_dump(exclude_none=True)
        elif hasattr(response, 'dict'):
            response_data = response.dict(exclude_none=True)
        elif isinstance(response, dict):
            response_data = response
        else:
            try:
                response_data = response.__dict__
            except:
                response_data = {"error": "Unable to serialize response"}
                logger.error("Failed to serialize MCP response")
        
        logger.debug(f"MCP response: {response_data}")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"MCP request handling failed: {e}")
        return jsonify({"error": f"MCP request handling failed: {str(e)}"}), 500


if __name__ == "__main__":
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    if log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        logging.getLogger().setLevel(getattr(logging, log_level))
        logger.info(f"Log level set to: {log_level}")
    
    port = int(os.environ.get("PORT", 5001))
    is_cloud = os.environ.get("K_SERVICE") is not None or os.environ.get("PORT") == "8080"
    environment = "Cloud" if is_cloud else "Local"
    
    logger.info(f"Starting MCP Weather Server on port {port} ({environment})")
    logger.info("API Configuration:")
    logger.info(f"   - Weather API: {WEATHER_API_PROTOCOL}://{WEATHER_API_HOST}:{WEATHER_API_PORT}")
    logger.info(f"   - Census API: {CENSUS_API_PROTOCOL}://{CENSUS_API_HOST}:{CENSUS_API_PORT}")
    logger.info(f"   - Nominatim API: {NOMINATIM_API_PROTOCOL}://{NOMINATIM_API_HOST}:{NOMINATIM_API_PORT}")
    logger.info(f"   - User Agent: {USER_AGENT}")
    
    app.run(host="0.0.0.0", port=port, debug=not is_cloud)
