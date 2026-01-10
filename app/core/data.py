"""
app/core/data.py

Handles persistent data storage and retrieval.
Responsible for loading/saving JSON configurations and importing Excel history.
"""

import json
import logging
import os
from typing import Dict, Optional

import pandas as pd

from app import constants as C
from app.models.config import AppConfig

logger = logging.getLogger(__name__)


class DataManager:
    """
    Static utility class for file I/O operations.
    """

    @staticmethod
    def load_config(filepath: str = C.CONFIG_FILE) -> AppConfig:
        """
        Loads the application configuration from a JSON file.

        If the file does not exist or is corrupted, a default configuration
        is generated and returned (safe fallback).

        Args:
            filepath (str): Path to the JSON config file.

        Returns:
            AppConfig: The loaded or default configuration object.
        """
        if not os.path.exists(filepath):
            logger.warning(f"Config file not found at {filepath}. Using defaults.")
            return AppConfig.default()

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return AppConfig.from_dict(data)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse config file: {e}. Using defaults.")
            return AppConfig.default()
        except Exception as e:
            logger.error(f"Unexpected error loading config: {e}. Using defaults.")
            return AppConfig.default()

    @staticmethod
    def save_config(config: AppConfig, filepath: str = C.CONFIG_FILE) -> bool:
        """
        Saves the current configuration to a JSON file.

        Uses a write-then-replace strategy (atomic write) to prevent data corruption
        if the process crashes during write.

        Args:
            config (AppConfig): The configuration object to save.
            filepath (str): Target file path.

        Returns:
            bool: True if save was successful, False otherwise.
        """
        tmp_path = f"{filepath}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(config.to_dict(), f, indent=4)

            # Atomic replacement
            if os.path.exists(filepath):
                os.replace(tmp_path, filepath)
            else:
                os.rename(tmp_path, filepath)

            logger.info("Configuration saved successfully.")
            return True
        except Exception as e:
            logger.error(f"Config save error: {e}")
            # Clean up temp file if it exists
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            return False

    @staticmethod
    def load_previous_balance(excel_path: Optional[str]) -> Dict[str, float]:
        """
        Imports 'Carry Over' points from a previous month's Excel roster.

        Args:
            excel_path (Optional[str]): Path to the Excel file.

        Returns:
            Dict[str, float]: A mapping of {Name: Carry Over Points}.
                              Returns an empty dict if path is None or invalid.

        Raises:
            ValueError: If required columns ('Name', 'Carry Over') are missing.
        """
        if not excel_path:
            return {}

        try:
            df = pd.read_excel(excel_path)

            # Normalize column names for robustness
            df.columns = [str(c).strip() for c in df.columns]

            if "Name" not in df.columns or "Carry Over" not in df.columns:
                raise ValueError("Excel file must contain 'Name' and 'Carry Over' columns.")

            balance = {}
            for _, row in df.iterrows():
                name = row["Name"]
                val = row["Carry Over"]

                # Ensure value is numeric
                try:
                    float_val = float(val)
                    balance[str(name)] = float_val
                except (ValueError, TypeError):
                    continue  # Skip invalid rows

            return balance
        except Exception as e:
            logger.error(f"Error loading previous balance: {e}")
            raise
