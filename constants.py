"""
constants.py

Central repository for all application constants.
Serves as the single source of truth for static values, colors, and defaults.
"""

from typing import List, Dict, Any

# --- Application Meta ---
APP_TITLE: str = "Duty Scheduler Pro - v6.4"
APP_GEOMETRY: str = "1280x850"
THEME_MODE: str = "Light"
THEME_COLOR: str = "blue"

# --- File Paths ---
CONFIG_FILE: str = "config.json"
DEFAULT_EXPORT_NAME: str = "Duty Plan for {month} {year}.xlsx"
LOG_FILE: str = "app.log"

# --- Excel Export Settings ---
EXCEL_SHEET_TITLE: str = "Duty Plan"
EXCEL_HEADERS_STATIC: List[str] = ["Name"]
EXCEL_HEADERS_SUFFIX: List[str] = ["Brought Fwd", "Month Pts", "Carry Over"]

# --- Color Palette (Hex) ---
COLOR_HEADER_BG: str = "#EEEEEE"
COLOR_PH_BG: str = "#FFEBEE"
COLOR_CONSTRAINT_BG: str = "#E0E0E0"

COLOR_CELL_DEFAULT: str = "#FFFFFF"
COLOR_CELL_X: str = "#E53935"
COLOR_CELL_AM: str = "#42A5F5"
COLOR_CELL_PM: str = "#1565C0"
COLOR_CELL_24H: str = "#8E24AA"
COLOR_CELL_PH: str = "#FF9800"

COLOR_TEXT_WHITE: str = "#FFFFFF"
COLOR_TEXT_BLACK: str = "#000000"

# --- Logic Defaults ---
SCORE_SCALE_FACTOR: int = 10
WEIGHT_POINTS_BALANCE: int = 100
WEIGHT_STANDBY_BALANCE: int = 1

SHIFT_TYPES: List[str] = ['AM', 'PM', '24H', 'S/B']
SCHEDULING_MODES: List[str] = ["shift", "24h", "hybrid"]

DEFAULT_CONFIG_TEMPLATE: Dict[str, Any] = {
    # workplace_name removed
    "year": 2025,
    "month": 1,
    "mode": "hybrid",
    "personnel": ["Alice", "Bob", "Charlie", "David", "Eve", "Frank"],
    "points": {
        "AM": 1.0,
        "PM": 1.0,
        "24H": 3.0,
        "S/B": 0.0,
        "weekend_multiplier": 1.5,
        "ph_multiplier": 2.0
    },
    "constraints": {
        "min_rest_after_24h": 1,
        "standby_per_day": 1,
        "personnel_needed_per_shift": {"AM": 1, "PM": 1, "24H": 1}
    }
}
