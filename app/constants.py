from enum import Enum

# --- FILE PATHS ---
CONFIG_FILE = "config.json"

# --- UI CONSTANTS ---
PAGE_TITLE = "Duty Planner"
APP_TITLE = PAGE_TITLE  # Alias for integration tests
PAGE_ICON = "📅"


class ScheduleMode(Enum):
    SHIFT = "SHIFT"  # AM / PM
    FULL_24H = "24H"  # 24H Only


# --- EXCEL EXPORT STYLES ---
EXCEL_SHEET_TITLE = "Duty Roster"
COLOR_HEADER_BG = "FFCCE5FF"  # Light Blue
COLOR_CONSTRAINT_BG = "FFFFFF00"  # Yellow for 'X'

# --- HEADERS ---
# The first column is always "Name"
EXCEL_HEADERS_STATIC = ["Name"]
# The last few columns are for stats
EXCEL_HEADERS_SUFFIX = ["Brought Fwd", "Month Pts", "Carry Over"]

# --- DUTY TYPES ---
# These are the values that contribute to points (usually)
# "X" is absence, not a duty.
ACTIVE_DUTIES = ["AM", "PM", "24H", "S/B"]
