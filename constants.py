"""
constants.py

Application Constants.
"""

from enum import Enum
from typing import List

APP_TITLE: str = "Duty Scheduler Pro - v8.1"
APP_GEOMETRY: str = "1280x850"
THEME_MODE: str = "Light"
THEME_COLOR: str = "blue"

CONFIG_FILE: str = "config.json"
EXCEL_SHEET_TITLE: str = "Duty Plan"
EXCEL_HEADERS_STATIC: List[str] = ["Name"]
EXCEL_HEADERS_SUFFIX: List[str] = ["Brought Fwd", "Month Pts", "Carry Over"]


class ShiftType(str, Enum):
    AM = "AM"
    PM = "PM"
    FULL_24H = "24H"
    STANDBY = "S/B"
    LEAVE = "X"
    EMPTY = ""


class ScheduleMode(str, Enum):
    SHIFT = "Shift"
    FULL_24H = "24H"


ACTIVE_DUTIES: List[str] = [
    ShiftType.AM,
    ShiftType.PM,
    ShiftType.FULL_24H,
    ShiftType.STANDBY,
]

COLOR_HEADER_BG: str = "#EEEEEE"
COLOR_PH_BG: str = "#FFEBEE"
COLOR_CONSTRAINT_BG: str = "#E0E0E0"

SHIFT_COLORS = {
    ShiftType.EMPTY: ("#FFFFFF", "#000000"),
    ShiftType.LEAVE: ("#E53935", "#FFFFFF"),
    ShiftType.AM: ("#42A5F5", "#FFFFFF"),
    ShiftType.PM: ("#1565C0", "#FFFFFF"),
    ShiftType.FULL_24H: ("#8E24AA", "#FFFFFF"),
    ShiftType.STANDBY: ("#FF9800", "#000000"),
}

SCORE_SCALE_FACTOR: int = 10
