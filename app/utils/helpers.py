"""
app/utils/helpers.py

Shared utility functions to avoid circular imports between logic and scheduler.
"""


def get_shift_name(base_type: str, team_num: int) -> str:
    """
    Returns the shift name, appending _N only if team_num > 1.
    e.g. ("AM", 1) -> "AM", ("AM", 2) -> "AM_2"

    Raises:
        ValueError: If team_num is less than 1.
    """
    if team_num < 1:
        raise ValueError(f"team_num must be >= 1, got {team_num}")
    return f"{base_type}_{team_num}" if team_num > 1 else base_type


def get_base_shift_type(shift_name: str) -> str:
    """
    Extracts the base shift type from a team shift string.
    e.g. "AM_2" -> "AM", "AM" -> "AM"

    Raises:
        ValueError: If shift_name is empty or invalid format.
    """
    if not shift_name:
        raise ValueError("shift_name cannot be empty")

    if "_" in shift_name:
        base = shift_name.split("_")[0]
        if not base:
            raise ValueError(f"Invalid shift_name format: '{shift_name}'")
        return base
    return shift_name
