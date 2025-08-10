"""MCP protocol endpoints for weather server"""
import logging
from flask import Blueprint, request, jsonify
from queue import Queue
import mcp_utils
from mcp_utils.core import MCPServer
from services.weather import WeatherService

logger = logging.getLogger(__name__)

mcp_bp = Blueprint('mcp', __name__)

# Initialize MCP server and weather service
response_queue = Queue()
weather_service = WeatherService()

# Initialize MCP server with fallback initialization patterns
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

# Register weather tool with MCP server
@mcp.tool()
def get_weather(city: str = None, zip_code: str = None):
    """Get weather information for a city or ZIP code"""
    return weather_service.get_weather(city=city, zip_code=zip_code)

@mcp_bp.route("/mcp", methods=["POST"])
def handle_mcp():
    """Handle MCP protocol requests"""
    body = request.get_json()
    logger.debug(f"MCP request received: {body}")
    
    try:
        response = mcp.handle_message(body)
        
        # Handle different response serialization methods
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
