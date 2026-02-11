"""
Logging configuration module.
Handles logging to both console and rotating file.
"""
import logging
import logging.handlers
import os
from time import strftime

# Create logs directory path
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
LOG_FILENAME = os.path.join(LOGS_DIR, strftime("bochk_monitor_%Y_%m_%d_%H.log"))


def _setup_logger():
    """Configure logger with console and file handlers."""
    # Ensure logs directory exists
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR, exist_ok=True)
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Log format
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (rotating)
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILENAME, maxBytes=10485760, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


# Initialize logger on module import
logger = _setup_logger()
