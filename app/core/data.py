"""
app/core/data.py

Handles persistent data storage and retrieval.
Responsible for loading JSON configurations and importing Excel history.
"""

import json
import logging
import os
from typing import Any, Dict, Union

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

    # REMOVED: save_config method to prevent server-side data leaks.

    @staticmethod
    def load_previous_balance(excel_file: Union[str, Any]) -> Dict[str, float]:
        """
        Imports 'Carry Over' points from a previous month's Excel roster.

        Args:
            excel_file: Path to the Excel file or a file-like object (BytesIO).

        Returns:
            Dict[str, float]: A mapping of {Name: Carry Over Points}.
                              Returns an empty dict if excel_file is falsy.

        Raises:
            ValueError: If required columns ('Name', 'Carry Over') are missing.
            Exception: Re-raises other parsing errors after logging.
        """
        if not excel_file:
            return {}

        try:
            # pandas read_excel supports both path and file-like objects
            df = pd.read_excel(excel_file)

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

    @staticmethod
    def load_constraints(excel_file: Union[str, Any]) -> Dict[str, Dict[int, str]]:
        """
        Imports constraints and duty requests from an Excel file.
        Expected format: Column 'Name', followed by numbered columns (1, 2, 3...) representing days.

        Args:
            excel_file: Path to the Excel file or a file-like object.

        Returns:
            Dict[str, Dict[int, str]]: A nested dict {Name: {DayNum: Value}}.
        """
        if not excel_file:
            return {}

        try:
            df = pd.read_excel(excel_file)
            # Normalize columns
            df.columns = [str(c).strip() for c in df.columns]

            if "Name" not in df.columns:
                raise ValueError("Excel file must contain 'Name' column.")

            constraints = {}
            # Identify day columns (digits like '1', '2', '30')
            day_cols = [c for c in df.columns if c.isdigit()]

            for _, row in df.iterrows():
                name = row["Name"]
                if not isinstance(name, str) or not name:
                    continue

                person_constraints = {}
                for day_str in day_cols:
                    val = row[day_str]
                    # Check for non-empty string values
                    if pd.notna(val):
                        val_str = str(val).strip().upper()
                        if val_str:
                            # Use int key for day to be generic
                            person_constraints[int(day_str)] = val_str

                if person_constraints:
                    constraints[name] = person_constraints

            return constraints
        except Exception as e:
            logger.error(f"Error loading constraints: {e}")
            raise
