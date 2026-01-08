import json
import os
from typing import Dict, Optional
import pandas as pd
from app import constants as C
from app.models.config import AppConfig

class DataManager:
    @staticmethod
    def load_config(filepath: str = C.CONFIG_FILE) -> AppConfig:
        if not os.path.exists(filepath):
            return AppConfig.default()
        
        try:
            # FIX: Explicit encoding
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return AppConfig.model_validate(data)
        except Exception as e:
            print(f"Config load error: {e}")
            return AppConfig.default()

    @staticmethod
    def save_config(config: AppConfig, filepath: str = C.CONFIG_FILE):
        try:
            # Use by_alias=True to save "24H" instead of "FULL_24H"
            data = config.model_dump(by_alias=True)
            # FIX: Explicit encoding
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Config save error: {e}")

    @staticmethod
    def load_previous_balance(filepath: str) -> Dict[str, float]:
        try:
            df = pd.read_excel(filepath)
            
            name_col = None
            balance_col = None
            
            for col in df.columns:
                c_str = str(col).lower().strip()
                if "name" in c_str:
                    name_col = col
                if "carry" in c_str and "over" in c_str:
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
            print(f"Import error: {e}")
            return {}
