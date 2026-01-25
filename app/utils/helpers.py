"""
app/utils/helpers.py

Shared utility functions to avoid circular imports between logic and scheduler.
"""


def get_shift_name(base_type: str, team_num: int) -> str:
    """
    Returns the shift name, appending _N only if team_num > 1.
    e.g. ("AM", 1) -> "AM", ("AM", 2) -> "AM_2"
    """
    return f"{base_type}_{team_num}" if team_num > 1 else base_type


def get_base_shift_type(shift_name: str) -> str:
    """
    Extracts the base shift type from a team shift string.
    e.g. "AM_2" -> "AM", "AM" -> "AM"
    """
    if "_" in shift_name:
        return shift_name.split("_")[0]
    return shift_name
