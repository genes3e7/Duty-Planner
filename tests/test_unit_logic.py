"""
tests/test_unit_logic.py

Focus: Logic Controller.
Verifies:
1. DataFrame generation (Empty schedule).
2. Statistics calculation (Month points, Carry over).
3. Constraint application.
"""

import pandas as pd
import pytest

from app import logic

# --- Day Parsing Tests ---


def test_get_day_num_valid():
    """Test valid day column parsing."""
    assert logic.get_day_num("D1") == 1
    assert logic.get_day_num("D31") == 31


def test_get_day_num_invalid():
    """Test defensive parsing of invalid day strings."""
    assert logic.get_day_num("D") == 0
    assert logic.get_day_num("D-1") == 0
    assert logic.get_day_num("DA") == 0
    assert logic.get_day_num("Random") == 0
    assert logic.get_day_num("") == 0
    assert logic.get_day_num(None) == 0


# --- Schedule Generation Tests ---


def test_generate_empty_schedule_structure():
    """Test that generated dataframes have correct shape and columns."""
    roster, days = logic.generate_empty_schedule(2025, 1, ["A", "B"])
    assert roster.shape == (2, 31)  # Jan has 31 days
    assert "D1" in roster.columns
    assert "D31" in roster.columns
    assert days.shape == (31, 5)  # Active, Mode, Is_PH, etc.
    assert days.index.name == "Day"


def test_generate_empty_schedule_invalid_date():
    """Test that invalid dates (e.g., month 13) raise ValueError."""
    with pytest.raises(ValueError, match="Invalid date generated"):
        logic.generate_empty_schedule(2025, 13, ["A"])


# --- Statistics Calculation Tests ---


def test_calculate_stats_multipliers(default_config):
    """Test point scoring logic with PH multiplier and weekend addition."""
    # 1. Sync Config with the Test Data Year/Month
    default_config.year = 2025
    default_config.month = 1
    default_config.personnel = ["TestUser"]

    # 2. Generate Data for Jan 2025
    roster, days = logic.generate_empty_schedule(2025, 1, ["TestUser"])

    pts = default_config.points
    pts.AM = 1.0
    pts.ph_multiplier = 2.0
    pts.weekend_multiplier = 1.5

    # Case A: PH (Multiplier) -> Jan 1 2025 is PH (New Year's)
    pts.ph_is_multiplier = True
    days.at[1, "Is_PH"] = True

    # Case B: Weekend (Addition) -> Jan 4 2025 is Saturday (Weekend)
    pts.weekend_is_multiplier = False

    # Assign Duties
    roster.at["TestUser", "D1"] = "AM"  # PH
    roster.at["TestUser", "D4"] = "AM"  # Weekend

    stats = logic.calculate_stats(roster, days, default_config, {})
    user_stats = stats.iloc[0]

    # D1 (PH): 1.0 * 2.0 = 2.0
    # D4 (Weekend): 1.0 + 1.5 = 2.5
    # Total = 4.5
    assert user_stats["Month Pts"] == 4.5


# --- Constraint Import Tests ---


def test_apply_imported_constraints_logic():
    """Test applying a dictionary of constraints to the dataframe."""
    roster = pd.DataFrame({"D1": ["", ""], "D2": ["", ""]}, index=["Alice", "Bob"])
    imported = {"Alice": {1: "AM"}, "Bob": {2: "X"}}

    result = logic.apply_imported_constraints(roster, imported)

    assert result.at["Alice", "D1"] == "AM"
    assert result.at["Bob", "D2"] == "X"
    # Ensure untouched remain empty
    assert result.at["Alice", "D2"] == ""


def test_apply_imported_constraints_partial_match():
    """Test handling of names that don't exist in the roster."""
    roster = pd.DataFrame({"D1": [""]}, index=["Alice"])

    imported = {
        "Charlie": {1: "AM"},  # Should be ignored
        "Alice": {1: "PM"},  # Should apply
    }

    result = logic.apply_imported_constraints(roster, imported)

    assert result.at["Alice", "D1"] == "PM"
    assert "Charlie" not in result.index
