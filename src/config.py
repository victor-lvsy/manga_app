"""Configuration for the application"""
import sys
from src.logger import Logger

logger = Logger("config")

if len(sys.argv) > 1 and sys.argv[1] == "dev":
    logger.info("Running in development mode")
    LOCAL_FOLDER = "/home/victor/Documents/manga_scraper/local_comics"
    RUN_MODE = "dev"
elif len(sys.argv) > 1 and sys.argv[1] == "prod":
    logger.info("Running in production mode")
    LOCAL_FOLDER = "/media/victor/DD_RPI/manga_reader"
    RUN_MODE = "prod"
else:
    logger.error("Invalid mode")
    sys.exit(1)
