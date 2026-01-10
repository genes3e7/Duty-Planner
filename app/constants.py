"""
app/constants.py

Holds global constants used across the application.
Includes color definitions, file paths, and default settings.
"""

from enum import Enum


class ScheduleMode(Enum):
    SHIFT = "SHIFT"
    FULL_24H = "24H"


# --- Application Settings ---
APP_TITLE = "Duty Planner"
CONFIG_FILE = "config.json"
EXCEL_SHEET_TITLE = "Duty Roster"

# --- Excel Headers ---
EXCEL_HEADERS_STATIC = ["Name"]
EXCEL_HEADERS_SUFFIX = ["Brought Fwd", "Month Pts", "Carry Over"]

# --- UI Colors (Hex) ---
COLOR_HEADER_BG = "#E0E0E0"
COLOR_CONSTRAINT_BG = "#FFCCCC"  # For 'X' assignments

# --- Logic Constants ---
# Set of duty strings that are considered "Active" for point calculation
ACTIVE_DUTIES = frozenset({"AM", "PM", "24H", "S/B"})
