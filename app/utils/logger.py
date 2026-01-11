"""
app/utils/logger.py

Provides a centralized logging configuration.
"""

import logging
import sys


def setup_logger(name: str = "app", level: int = logging.INFO) -> logging.Logger:
    """
    Configures and returns a logger instance.

    Args:
        name (str): Name of the logger.
        level (int): Logging level (default: logging.INFO).

    Returns:
        logging.Logger: Configured logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False  # Prevent propagation to avoid duplicates

    # Check if handlers already exist to avoid duplicates
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
