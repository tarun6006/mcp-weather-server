"""
Refactored Weather MCP Server
Modular architecture with separated concerns
"""
import os
import logging
from flask import Flask
from config.settings import setup_logging, log_configuration
from routes.health import health_bp
from routes.mcp import mcp_bp

# Setup logging first
setup_logging()

# Create Flask app
app = Flask(__name__)

# Register blueprints
app.register_blueprint(health_bp)
app.register_blueprint(mcp_bp)

# Log configuration
log_configuration()

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    if log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        logging.getLogger().setLevel(getattr(logging, log_level))
        logger.info(f"Log level set to: {log_level}")
    
    port = int(os.environ.get("PORT", 5001))
    is_cloud = os.environ.get("K_SERVICE") is not None or os.environ.get("PORT") == "8080"
    environment = "Cloud" if is_cloud else "Local"
    
    logger.info(f"Starting Weather MCP Server on port {port} ({environment})")
    logger.info("Features Enabled:")
    logger.info("   - MCP (Model Context Protocol) support")
    logger.info("   - Multi-API geocoding (Census + Nominatim)")
    logger.info("   - National Weather Service integration")
    logger.info("   - ZIP code and city resolution")
    
    app.run(host="0.0.0.0", port=port, debug=not is_cloud)
