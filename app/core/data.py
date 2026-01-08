import json
import os
import logging
from typing import Dict
import pandas as pd
from app import constants as C
from app.models.config import AppConfig

logger = logging.getLogger(__name__)

class DataManager:
    @staticmethod
    def load_config(filepath: str = C.CONFIG_FILE) -> AppConfig:
        if not os.path.exists(filepath):
            return AppConfig.default()
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return AppConfig.model_validate(data)
        except Exception as e:
            logger.warning(f"Config load error: {e}")
            return AppConfig.default()

    @staticmethod
    def save_config(config: AppConfig, filepath: str = C.CONFIG_FILE):
        try:
            data = config.model_dump(by_alias=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Config save error: {e}")

    @staticmethod
    def load_previous_balance(filepath: str) -> Dict[str, float]:
        try:
            df = pd.read_excel(filepath)
            
            name_col = None
            balance_col = None
            
            for col in df.columns:
                c_str = str(col).lower().strip()
                # Precise matching
                if c_str == "name" or c_str.startswith("name ") or c_str.endswith(" name"):
                    name_col = col
                if "carry over" in c_str or "carryover" in c_str:
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
            return {}
