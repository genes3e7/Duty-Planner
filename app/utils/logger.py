"""
logger.py

Handles the initialization of the application's logging infrastructure.
Writes logs to both disk (app.log) and console.
"""

import logging
import sys

# UPDATED IMPORT
from app import constants as C


def setup_logger() -> None:
    """
    Configures the root logger.
    Sets up FileHandler and StreamHandler with formatting.
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Clear existing handlers to prevent duplication on reload
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(module)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. File Handler
    try:
        file_handler = logging.FileHandler(C.LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except PermissionError:
        print(f"WARNING: Could not write to {C.LOG_FILE}. Logging disabled.")
    except Exception as e:
        print(f"CRITICAL: Logger init failed: {e}")

    # 2. Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logging.info("=== Application Started ===")
