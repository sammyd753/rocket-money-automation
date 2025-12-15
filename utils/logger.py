"""Logging utilities for Rocket Money automation."""

import logging

# Configure logging
logging.basicConfig(
    filename="automation.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def log(message, level="info"):
    """Log a message to both file and console.
    
    Args:
        message: The message to log
        level: Log level - "info" or "error"
    """
    if level == "info":
        logging.info(message)
    elif level == "error":
        logging.error(message)
    print(message)

