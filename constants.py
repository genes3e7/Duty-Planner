"""
constants.py

Central repository for all application constants.
This file serves as the single source of truth for static values, ensuring
maintainability and preventing 'magic numbers' in the logic code.

Standards:
- All constants are uppercase (PEP 8).
- Type hints provided for clarity.
"""

from typing import List, Dict, Any

# --- File Paths ---
CONFIG_FILE: str = "config.json"
DEFAULT_EXPORT_NAME: str = "{workplace} Duty Plan for {month} {year}.xlsx"
LOG_FILE: str = "app.log"

# --- GUI Settings ---
APP_TITLE: str = "Duty Scheduler Pro - v2.4"
APP_GEOMETRY: str = "850x750"
THEME_MODE: str = "System"  # Options: "System", "Dark", "Light"
THEME_COLOR: str = "blue"   # Options: "blue", "green", "dark-blue"

# --- Excel Export Settings ---
EXCEL_SHEET_TITLE: str = "Duty Plan"
EXCEL_HEADERS_STATIC: List[str] = ["Name"]
EXCEL_HEADERS_SUFFIX: List[str] = ["Brought Fwd", "Month Pts", "Carry Over"]

# Excel Styling Colors (Hex Codes)
COLOR_HEADER_BG: str = "DDDDDD"       # Light Grey
COLOR_PH_BG: str = "FFCCCC"           # Light Red
COLOR_CONSTRAINT_BG: str = "AAAAAA"   # Dark Grey for 'X' cells

# --- Scheduler Engine Settings ---
# Multiplier to handle floating point math in an Integer solver (e.g. 1.5 -> 15)
SCORE_SCALE_FACTOR: int = 10

# Solver Objective Weights
WEIGHT_POINTS_BALANCE: int = 100      # Priority 1: Equalize points
WEIGHT_STANDBY_BALANCE: int = 1       # Priority 2: Equalize standby count

# --- Logic Defaults ---
SHIFT_TYPES: List[str] = ['AM', 'PM', '24H', 'S/B']
SCHEDULING_MODES: List[str] = ["shift", "24h", "hybrid"]

# Default Configuration Template
DEFAULT_CONFIG_TEMPLATE: Dict[str, Any] = {
    "workplace_name": "My Unit",
    "year": 2025,
    "month": 1,
    "mode": "hybrid",
    "personnel": ["Alice", "Bob", "Charlie", "David", "Eve", "Frank"],
    "points": {
        "AM": 1,
        "PM": 1,
        "24H": 3,
        "S/B": 0,
        "weekend_multiplier": 1.5,
        "ph_multiplier": 2.0
    },
    "constraints": {
        "min_rest_after_24h": 1,
        "standby_per_day": 1,
        "personnel_needed_per_shift": {"AM": 1, "PM": 1, "24H": 1}
    }
}
