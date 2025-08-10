"""Health check endpoints for weather server"""
import time
import logging
from flask import Blueprint, jsonify

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for the weather MCP server"""
    try:
        return jsonify({
            "status": "healthy",
            "server": "weather-server",
            "version": "1.0",
            "timestamp": time.time(),
            "services": {
                "weather_api": True,
                "census_api": True,
                "nominatim_api": True,
                "mcp_protocol": True
            }
        }), 200
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }), 500
