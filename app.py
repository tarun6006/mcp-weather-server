import os
import requests
from flask import Flask, request, jsonify
from mcp_utils.core import MCPServer
from mcp_utils.schema import GetPromptResult, Message, TextContent, CallToolResult
from dotenv import load_dotenv

load_dotenv()
USER_AGENT = os.getenv("NWS_USER_AGENT", "myapp@example.com")

mcp = MCPServer("weather-server", "1.0")

@mcp.prompt()
def weather_prompt(city: str = None, zip_code: str = None) -> GetPromptResult:
    desc = f"Get weather for {city or zip_code}"
    msg = TextContent(text=f"Fetch weather for {city or zip_code}")
    return GetPromptResult(description=desc, messages=[Message(role="user", content=msg)])

@mcp.tool()
def get_weather(city: str = None, zip_code: str = None) -> CallToolResult:
    # geocode via weather.gov points endpoint
    if zip_code:
        # use zippopotam.us for lat/lon lookup
        r = requests.get(f"https://api.zippopotam.us/us/{zip_code}")
        r.raise_for_status()
        data = r.json()
        lat, lon = data['places'][0]['latitude'], data['places'][0]['longitude']
    else:
        # use geocode service or skip – for brevity use city name geocoding via geopy is example
        from geopy.geocoders import Nominatim
        geol = Nominatim(user_agent="weather-app")
        loc = geol.geocode(city)
        lat, lon = loc.latitude, loc.longitude

    headers = {"User-Agent": USER_AGENT}
    pt = requests.get(f"https://api.weather.gov/points/{lat},{lon}", headers=headers)
    pt.raise_for_status()
    forecast_url = pt.json()['properties']['forecast']
    f = requests.get(forecast_url, headers=headers)
    f.raise_for_status()
    periods = f.json()['properties']['periods']
    summary = periods[0]['shortForecast']
    temp = periods[0]['temperature']
    result = f"{summary}, {temp}°{periods[0]['temperatureUnit']}"
    return CallToolResult(content=result)

app = Flask(__name__)
@app.route("/mcp", methods=["POST"])
def mcp_route():
    resp = mcp.handle_message(request.get_json())
    return jsonify(resp.model_dump(exclude_none=True))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
