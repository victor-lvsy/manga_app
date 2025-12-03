"""Configuration for the application"""
import sys
import os
from src.logger import Logger

logger = Logger("config")

LOCAL_FOLDER = "/app/local_comics"

if len(sys.argv) > 1 and sys.argv[1] == "dev":
    logger.info("Running in development mode")
elif len(sys.argv) > 1 and sys.argv[1] == "prod":
    logger.info("Running in production mode")
else:
    logger.error("Invalid mode")
    sys.exit(1)

if os.getenv("IAM") == "reader":
    if os.getenv("HTTP_SCHEME") == "http":
        HTTP_SCHEME = "http"
    elif os.getenv("HTTP_SCHEME") == "https":
        HTTP_SCHEME = "https"
    else:
        logger.error("Invalid HTTP scheme")
        sys.exit(1)
elif os.getenv("IAM") == "scraper":
    pass
else:
    logger.error("Invalid IAM")
    sys.exit(1)