"""
app/utils/logger.py

Provides utility functions for configuring the application's logging system.
This ensures consistent log formatting and output levels across all modules.
"""

import logging
import sys


def setup_logger(name: str = "app", level: int = logging.INFO) -> logging.Logger:
    """
    Configures and returns a logger instance with a standard format.

    The logger is configured to output to stdout with a format including
    timestamp, logger name, level, and message.

    Args:
        name (str): The name of the logger (usually __name__). Defaults to "app".
        level (int): The logging severity level (e.g., logging.INFO, logging.DEBUG).
                     Defaults to logging.INFO.

    Returns:
        logging.Logger: A configured standard Python logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding multiple handlers if setup is called multiple times
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
