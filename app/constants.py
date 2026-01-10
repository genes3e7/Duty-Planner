"""
app/constants.py

Global constants used throughout the Duty Planner application.

This module defines configuration for:
- File paths and naming conventions.
- Excel export settings (headers, sheet names).
- UI colors and styling constants.
- Enumerations for scheduling modes.
"""

from enum import Enum

# --- Application Metadata ---
APP_TITLE = "Duty Planner"
APP_ICON = "📅"
VERSION = "1.0.0"

# --- File Paths ---
CONFIG_FILE = "config.json"
"""Path to the main JSON configuration file."""

# --- Excel Export Settings ---
EXCEL_SHEET_TITLE = "Duty Roster"
"""Title of the worksheet in the exported Excel file."""

# Headers for the export columns
EXCEL_HEADERS_STATIC = ["Name"]
EXCEL_HEADERS_SUFFIX = ["Brought Fwd", "Month Pts", "Carry Over"]

# --- UI Styling & Colors ---
# Hex codes used for conditional formatting in the UI and Excel
COLOR_HEADER_BG = "#E6E6E6"  # Light Gray
COLOR_CONSTRAINT_BG = "#FFCCCC"  # Light Red (for 'X')
COLOR_SUCCESS_BG = "#CCFFCC"  # Light Green


# --- Scheduling Constants ---
class ScheduleMode(Enum):
    """
    Enumeration for the operational mode of a specific day.
    """

    SHIFT = "SHIFT"
    """Standard shift mode (AM/PM)."""

    FULL_24H = "24H"
    """24-hour duty mode (typically for Holidays)."""


# List of duty strings that are considered "Active" for point calculation
ACTIVE_DUTIES = ["AM", "PM", "24H", "S/B"]
"""Duty codes that contribute to a user's score."""
