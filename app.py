import os
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from queue import Queue
import mcp_utils
from mcp_utils.core import MCPServer
from mcp_utils.schema import GetPromptResult, Message, TextContent, CallToolResult
from geopy.geocoders import Nominatim
from requests.exceptions import HTTPError, RequestException

load_dotenv()

# Configuration from environment variables
USER_AGENT = os.getenv("NWS_USER_AGENT", "test@example.com")

# Weather.gov API configuration
WEATHER_API_HOST = os.getenv("WEATHER_API_HOST", "api.weather.gov")
WEATHER_API_PORT = os.getenv("WEATHER_API_PORT", "443")
WEATHER_API_PROTOCOL = os.getenv("WEATHER_API_PROTOCOL", "https")
WEATHER_API_POINTS_PATH = os.getenv("WEATHER_API_POINTS_PATH", "/points")

# ZIP Code Resolution APIs configuration
# Primary: US Census API (most authoritative for US addresses)
CENSUS_API_HOST = os.getenv("CENSUS_API_HOST", "geocoding.geo.census.gov")
CENSUS_API_PORT = os.getenv("CENSUS_API_PORT", "443")
CENSUS_API_PROTOCOL = os.getenv("CENSUS_API_PROTOCOL", "https")
CENSUS_API_PATH = os.getenv("CENSUS_API_PATH", "/geocoder/locations/onelineaddress")

# Secondary: Nominatim/OpenStreetMap configuration
NOMINATIM_API_HOST = os.getenv("NOMINATIM_API_HOST", "nominatim.openstreetmap.org")
NOMINATIM_API_PORT = os.getenv("NOMINATIM_API_PORT", "443")
NOMINATIM_API_PROTOCOL = os.getenv("NOMINATIM_API_PROTOCOL", "https")
NOMINATIM_API_PATH = os.getenv("NOMINATIM_API_PATH", "/search")

app = Flask(__name__)
response_queue = Queue()

# Initialize MCPServer with error handling for different versions
try:
    # Try the original pattern with response_queue
    mcp = MCPServer("weather-server", "1.0", response_queue)
except TypeError as e:
    print(f"First attempt failed: {e}")
    try:
        # Try without response_queue (some versions might not need it)
        mcp = MCPServer("weather-server", "1.0")
        # Set response_queue as attribute if needed
        if hasattr(mcp, 'response_queue'):
            mcp.response_queue = response_queue
    except Exception as e2:
        print(f"Second attempt failed: {e2}")
        # Try with keyword arguments
        mcp = MCPServer(name="weather-server", version="1.0")
        if hasattr(mcp, 'response_queue'):
            mcp.response_queue = response_queue


def build_api_url(host, port, protocol, path=""):
    """Helper function to build API URLs from components"""
    port_str = f":{port}" if port != "443" and port != "80" else ""
    return f"{protocol}://{host}{port_str}{path}"

def resolve_zip_code_improved(zip_code):
    """
    ZIP code resolution using only free, reliable APIs:
    1. US Census API (most authoritative for US ZIP codes)
    2. Nominatim/OpenStreetMap (free fallback)
    """
    
    # Method 1: US Census Geocoding API (Primary - most authoritative for US)
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
                print(f"✅ Census API resolved {zip_code}: ({lat}, {lon})")
                return lat, lon
    except Exception as e:
        print(f"⚠️ Census API failed: {e}")
    
    # Method 2: Nominatim/OpenStreetMap (Secondary - free fallback)
    try:
        nominatim_url = build_api_url(NOMINATIM_API_HOST, NOMINATIM_API_PORT, NOMINATIM_API_PROTOCOL)
        geolocator = Nominatim(user_agent="weather-mcp-improved", domain=nominatim_url.replace("https://", "").replace("http://", ""))
        
        # Try different ZIP code query formats for better success rate
        formats = [
            f"postcode:{zip_code}, country:US",  # Structured query
            f"{zip_code}, United States",        # Full country name
            f"{zip_code}, USA",                  # Country abbreviation
            f"{zip_code}, US"                    # Short abbreviation
        ]
        
        for zip_format in formats:
            try:
                location = geolocator.geocode(zip_format, country_codes='us', timeout=15)
                if location:
                    print(f"✅ Nominatim resolved {zip_code}: {location.address}")
                    return location.latitude, location.longitude
            except Exception:
                continue
    except Exception as e:
        print(f"⚠️ Nominatim failed: {e}")
    
    print(f"❌ Both Census and Nominatim failed for ZIP code {zip_code}")
    return None, None


@mcp.tool()
def get_weather(city: str = None, zip_code: str = None) -> CallToolResult:
    try:
        if zip_code:
            lat, lon = resolve_zip_code_improved(zip_code)
            if lat is None or lon is None:
                raise ValueError(f"Could not resolve ZIP code {zip_code}")
        elif city:
            geolocator = Nominatim(user_agent="weather-mcp")
            loc = geolocator.geocode(city, timeout=5)
            if not loc:
                raise ValueError("Location not found")
            lat, lon = loc.latitude, loc.longitude
        else:
            raise ValueError("Provide city or zip_code")

        headers = {"User-Agent": USER_AGENT}
        weather_base_url = build_api_url(WEATHER_API_HOST, WEATHER_API_PORT, WEATHER_API_PROTOCOL)
        
        # Get weather station grid points
        points_url = f"{weather_base_url}{WEATHER_API_POINTS_PATH}/{lat},{lon}"
        point_resp = requests.get(points_url, headers=headers, timeout=10)
        point_resp.raise_for_status()
        forecast_url = point_resp.json()['properties']['forecast']

        # Get weather forecast
        forecast_resp = requests.get(forecast_url, headers=headers, timeout=10)
        forecast_resp.raise_for_status()
        data = forecast_resp.json()['properties']['periods'][0]

        forecast_text = f"{data['name']}: {data['shortForecast']} at {data['temperature']}°{data['temperatureUnit']}"
        return CallToolResult(content=[TextContent(type='text', text=forecast_text)])

    except Exception as e:
        return CallToolResult(content=[TextContent(type='text', text=f"Error: {str(e)}")])


@app.route("/mcp", methods=["POST"])
def handle_mcp():
    body = request.get_json()
    response = mcp.handle_message(body)
    
    # Handle different response types safely
    if hasattr(response, 'model_dump'):
        # Pydantic v2 style
        response_data = response.model_dump(exclude_none=True)
    elif hasattr(response, 'dict'):
        # Pydantic v1 style
        response_data = response.dict(exclude_none=True)
    elif isinstance(response, dict):
        # Already a dictionary
        response_data = response
    else:
        # Convert to dict if possible
        try:
            response_data = response.__dict__
        except:
            response_data = {"error": "Unable to serialize response"}
    
    return jsonify(response_data), 200


if __name__ == "__main__":
    # Use port 8080 for Google Cloud deployment, 5001 for local development
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
