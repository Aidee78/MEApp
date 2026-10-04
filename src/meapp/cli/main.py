import logging

from meapp.logging.setup import setup_logging
from meapp.config import settings


def main():
    # First configure the logging infrastructure. Then obtain and use the application logger. 
    # Configure logging before the application starts emitting log records that depend on your logging configuration.
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("MEApp started.")

    settings.Settings.validate()
