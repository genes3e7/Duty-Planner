"""
tests/test_helpers.py

Unit tests for the utility helper functions in app/utils/helpers.py.
"""

from app.utils import helpers


def test_get_shift_name_team_1():
    """Test that Team 1 does NOT append a suffix."""
    assert helpers.get_shift_name("AM", 1) == "AM"
    assert helpers.get_shift_name("S/B", 1) == "S/B"


def test_get_shift_name_team_N():
    """Test that Team N (N > 1) appends _N."""
    assert helpers.get_shift_name("AM", 2) == "AM_2"
    assert helpers.get_shift_name("PM", 3) == "PM_3"
    assert helpers.get_shift_name("24H", 10) == "24H_10"


def test_get_base_shift_type_standard():
    """Test extraction of base type from standard shifts."""
    assert helpers.get_base_shift_type("AM") == "AM"
    assert helpers.get_base_shift_type("24H") == "24H"


def test_get_base_shift_type_with_suffix():
    """Test extraction of base type from team shifts."""
    assert helpers.get_base_shift_type("AM_2") == "AM"
    assert helpers.get_base_shift_type("PM_99") == "PM"
    assert helpers.get_base_shift_type("S/B_2") == "S/B"
