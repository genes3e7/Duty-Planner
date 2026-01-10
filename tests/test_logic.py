"""
tests/test_logic.py

Tests for the application logic controller.
Includes boundary tests, error handling, and data transformation checks.
"""

import pandas as pd

from app import logic

# Note: default_config fixture is available from conftest.py


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


def test_generate_empty_schedule_structure():
    """Test that generated dataframes have correct shape and columns."""
    roster, days = logic.generate_empty_schedule(2025, 1, ["A", "B"])

    assert roster.shape == (2, 31)  # Jan has 31 days
    assert "D1" in roster.columns
    assert "D31" in roster.columns
    assert days.shape == (31, 5)  # Active, Mode, Is_PH, etc.
    assert days.index.name == "Day"


def test_generate_empty_schedule_invalid_date():
    """Test fallback behavior for invalid dates (e.g., month 13)."""
    # Assuming the logic defaults to 30 days on error as per docstring
    # logic.py uses pd.Period to determine days in month, which raises error for month 13
    # It catches this error and returns 30.
    roster, days = logic.generate_empty_schedule(2025, 13, ["A"])
    assert roster.shape == (1, 30)


def test_calculate_stats_multipliers(default_config):
    """Exhaustive test of point scoring logic."""
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

    # Case A: PH (Multiplier)
    # Jan 1 2025 is PH (New Year's)
    pts.ph_is_multiplier = True
    days.at[1, "Is_PH"] = True

    # Case B: Weekend (Addition)
    # Jan 4 2025 is Saturday (Weekend)
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


def test_synchronize_roster_defensive():
    """Test synchronization with empty or None inputs."""
    assert logic.synchronize_roster_index(None, []) is None

    df = pd.DataFrame({"D1": ["AM"]}, index=["Old"])
    new_df = logic.synchronize_roster_index(df, ["New"])

    assert "New" in new_df.index
    assert "Old" not in new_df.index
    assert new_df.at["New", "D1"] == ""
