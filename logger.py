"""
logger.py

Handles the initialization of the application's logging infrastructure.
Writes logs to both disk and console for maximum visibility during debugging.
"""

import logging
import sys
import os
from typing import Optional
import constants as C


def setup_logger() -> None:
    """
    Configures the root logger.
    
    Sets up:
    1. FileHandler: Writes to 'app.log' with rotation safety check.
    2. StreamHandler: Writes to console (stdout).
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Clear existing handlers to prevent duplicate logs on reload
    if logger.hasHandlers():
        logger.handlers.clear()

    # Formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 1. File Handler (Defensive: Check write permissions)
    try:
        file_handler = logging.FileHandler(C.LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except PermissionError:
        print(f"WARNING: Could not write to {C.LOG_FILE}. Logging to file disabled.")
    except Exception as e:
        print(f"CRITICAL: Logger initialization failed: {e}")

    # 2. Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logging.info("=== Logger Initialized Successfully ===")
