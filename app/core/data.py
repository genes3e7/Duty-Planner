import json
import logging
import os
from typing import Dict

import pandas as pd

from app import constants as C
from app.models.config import AppConfig

logger = logging.getLogger(__name__)


class DataManager:
    """
    Handles all persistence logic (Loading/Saving files).
    Separates file I/O from the application logic.
    """

    @staticmethod
    def load_config(filepath: str = C.CONFIG_FILE) -> AppConfig:
        """
        Loads the application configuration from a JSON file.
        Returns a default configuration if the file is missing or corrupted.
        """
        if not os.path.exists(filepath):
            return AppConfig.default()

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return AppConfig.model_validate(data)
        except json.JSONDecodeError as e:
            logger.warning(f"Config file corrupted (invalid JSON): {e}")
            return AppConfig.default()
        except (OSError, IOError) as e:
            logger.warning(f"Config file I/O error: {e}")
            return AppConfig.default()
        except Exception as e:
            logger.warning(f"Config load error: {e}")
            return AppConfig.default()

    @staticmethod
    def save_config(config: AppConfig, filepath: str = C.CONFIG_FILE) -> bool:
        """
        Saves the current configuration to disk.
        Returns True if successful, False otherwise.
        """
        try:
            data = config.model_dump(by_alias=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Config save error: {e}")
            return False

    @staticmethod
    def load_previous_balance(filepath: str) -> Dict[str, float]:
        """
        Parses an Excel export file to extract 'Carry Over' points.
        Uses heuristic matching to find the 'Name' and 'Carry Over' columns.

        Args:
            filepath (str): Path to the uploaded Excel file.

        Returns:
            Dict[str, float]: Map of Name -> Points.
        """
        try:
            df = pd.read_excel(filepath)

            name_col = None
            balance_col = None

            # Fuzzy matching for columns
            for col in df.columns:
                c_str = str(col).lower().strip()

                # Prefer exact match; only accept partial if no exact match found
                if c_str == "name":
                    name_col = col  # Exact match takes priority
                elif name_col is None and (c_str.startswith("name ") or c_str.endswith(" name")):
                    name_col = col

                if c_str == "carry over" or c_str == "carryover":
                    balance_col = col  # Exact match takes priority
                elif balance_col is None and ("carry over" in c_str or "carryover" in c_str):
                    balance_col = col

            if not name_col or not balance_col:
                raise ValueError("Could not find 'Name' or 'Carry Over' columns.")

            balance_map = {}
            for _, row in df.iterrows():
                name = row[name_col]
                val = row[balance_col]
                if pd.notna(name) and pd.notna(val):
                    try:
                        balance_map[str(name)] = float(val)
                    except ValueError:
                        continue

            return balance_map

        except Exception as e:
            logger.error(f"Import error: {e}")
            raise  # Re-raise to allow UI to show specific error
