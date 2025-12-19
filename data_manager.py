"""
data_manager.py

Handles all File Input/Output operations including:
- JSON Configuration loading/saving.
- Excel Exporting with formatting.
- Importing previous balances (fuzzy matching).
"""

import json
import os
import re
import logging
from typing import Dict, List, Any, Tuple
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side # type: ignore
import constants as C

class DataManager:
    """Static utility class for file handling."""

    @staticmethod
    def load_config(filepath: str = C.CONFIG_FILE) -> Dict[str, Any]:
        """Loads config or returns default if missing/corrupt."""
        if not os.path.exists(filepath):
            logging.warning("Config not found. Loading defaults.")
            return C.DEFAULT_CONFIG_TEMPLATE.copy()
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                merged = C.DEFAULT_CONFIG_TEMPLATE.copy()
                merged.update(data)
                return merged
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Config load error: {e}")
            return C.DEFAULT_CONFIG_TEMPLATE.copy()

    @staticmethod
    def save_config(data: Dict[str, Any], filepath: str = C.CONFIG_FILE) -> None:
        """Saves configuration to JSON."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            logging.info("Configuration saved.")
        except IOError as e:
            logging.error(f"Config save failed: {e}")
            raise IOError(f"Could not save settings: {str(e)}")

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Removes illegal characters from filenames."""
        return re.sub(r'[\\/*?:"<>|]', "", filename)

    @staticmethod
    def load_previous_balance(filepath: str) -> Dict[str, float]:
        """
        Parses an Excel file to extract 'Name' and 'Carry Over' columns.
        Uses fuzzy matching for column names.
        """
        if not filepath or not os.path.exists(filepath):
            raise FileNotFoundError("File does not exist.")

        try:
            df = pd.read_excel(filepath)
            # Normalize columns
            cols = [str(c).lower().strip() for c in df.columns]
            
            # Find indices
            name_idx = next((i for i, c in enumerate(cols) if 'name' in c), None)
            bal_idx = next((i for i, c in enumerate(cols) 
                            if any(x in c for x in ['carry', 'bal', 'roll'])), None)

            if name_idx is None or bal_idx is None:
                raise ValueError("Could not find 'Name' or 'Carry Over' columns.")

            result: Dict[str, float] = {}
            for _, row in df.iterrows():
                try:
                    raw_name = row[df.columns[name_idx]]
                    raw_val = row[df.columns[bal_idx]]
                    
                    if pd.isna(raw_name) or pd.isna(raw_val): continue
                    
                    name_key = str(raw_name).strip()
                    val = float(raw_val)
                    result[name_key] = val
                except (ValueError, TypeError):
                    continue
            
            return result
        except Exception as e:
            logging.error(f"Import failed: {e}")
            raise e

    @staticmethod
    def export_schedule(
        schedule_data: Dict[Any, str],
        point_summary: List[Dict[str, Any]],
        config: Dict[str, Any],
        leaves: List[Tuple[str, int]],
        save_path: str
    ) -> str:
        """Exports the generated schedule to a formatted Excel file."""
        try:
            days = max([k[1] for k in schedule_data.keys()]) if schedule_data else 30
            names = sorted(config.get('personnel', []))
            
            wb = Workbook()
            ws = wb.active
            ws.title = C.EXCEL_SHEET_TITLE
            
            # Headers
            headers = C.EXCEL_HEADERS_STATIC + [d for d in range(1, days+1)] + C.EXCEL_HEADERS_SUFFIX
            ws.append(headers)
            
            pt_map = {str(i['Name']): i for i in point_summary}
            
            for name in names:
                row = [name]
                for d in range(1, days+1):
                    # Check manual constraint or schedule
                    if (name, d) in leaves: 
                        row.append("X")
                    else: 
                        row.append(schedule_data.get((name, d), ""))
                
                p = pt_map.get(name, {'Brought Fwd': 0.0, 'Month Pts': 0.0, 'Carry Over': 0.0})
                row.extend([p['Brought Fwd'], p['Month Pts'], p['Carry Over']])
                ws.append(row)

            # Styling
            c_header = C.COLOR_HEADER_BG.replace("#", "")
            c_x = C.COLOR_CONSTRAINT_BG.replace("#", "")

            fill_header = PatternFill("solid", fgColor=c_header)
            fill_x = PatternFill("solid", fgColor=c_x)
            thin_border = Side(style='thin')
            border = Border(left=thin_border, right=thin_border, top=thin_border, bottom=thin_border)

            for excel_row in ws.iter_rows(min_row=1, max_row=ws.max_row):
                for cell in excel_row:
                    cell.border = border
                    cell.alignment = Alignment(horizontal="center")
                    if cell.row == 1: 
                        cell.font = Font(bold=True)
                        cell.fill = fill_header
                    if cell.value == "X": 
                        cell.fill = fill_x
            
            wb.save(save_path)
            logging.info(f"Exported to {save_path}")
            return f"Successfully saved to:\n{save_path}"
        except Exception as e:
            logging.error(f"Export failed: {e}")
            raise e
