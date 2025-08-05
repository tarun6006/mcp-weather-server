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
USER_AGENT = os.getenv("NWS_USER_AGENT", "test@example.com")

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


@mcp.tool()
def get_weather(city: str = None, zip_code: str = None) -> CallToolResult:
    try:
        if zip_code:
            resp = requests.get(f"https://api.zippopotam.us/us/{zip_code}", timeout=5)
            resp.raise_for_status()
            data = resp.json()
            lat = data['places'][0]['latitude']
            lon = data['places'][0]['longitude']
        elif city:
            geolocator = Nominatim(user_agent="weather-mcp")
            loc = geolocator.geocode(city, timeout=5)
            if not loc:
                raise ValueError("Location not found")
            lat, lon = loc.latitude, loc.longitude
        else:
            raise ValueError("Provide city or zip_code")

        headers = {"User-Agent": USER_AGENT}
        point = requests.get(f"https://api.weather.gov/points/{lat},{lon}", headers=headers, timeout=5)
        point.raise_for_status()
        forecast_url = point.json()['properties']['forecast']

        forecast = requests.get(forecast_url, headers=headers, timeout=5)
        forecast.raise_for_status()
        data = forecast.json()['properties']['periods'][0]

        forecast_text = f"{data['name']}: {data['shortForecast']} at {data['temperature']}°{data['temperatureUnit']}"
        return CallToolResult(content=[TextContent(type='text', text=forecast_text)])

    except Exception as e:
        return CallToolResult(content=[TextContent(type='text', text=f"Error: {str(e)}")])


@app.route("/mcp", methods=["POST"])
def handle_mcp():
    body = request.get_json()
    response = mcp.handle_message(body)
    return jsonify(response.model_dump(exclude_none=True)), 200


if __name__ == "__main__":
    # Use port 8080 for Google Cloud deployment, 5001 for local development
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
