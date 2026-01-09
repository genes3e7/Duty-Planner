import pandas as pd
import pytest

from app import logic
from app.models.config import AppConfig


@pytest.fixture
def default_config():
    return AppConfig.default()


def test_get_day_num_parsing():
    """Test the robust day number parser."""
    assert logic.get_day_num("D1") == 1
    assert logic.get_day_num("D31") == 31
    assert logic.get_day_num("D05") == 5
    # Edge cases
    # Strict parsing now requires 'D' prefix to avoid false positives (e.g. 'Date' -> 'ate')
    assert logic.get_day_num("1") == 0
    assert logic.get_day_num("Invalid") == 0
    assert logic.get_day_num(None) == 0


def test_generate_schedule_structure(default_config):
    """Test generation of empty dataframes for a specific month."""
    # Test Leap Year (Feb 2024 = 29 days)
    roster, days = logic.generate_empty_schedule(2024, 2, ["A", "B"])

    assert len(days) == 29
    assert len(roster.columns) == 29
    assert roster.columns[0] == "D1"
    assert roster.columns[-1] == "D29"
    assert len(roster) == 2

    # Verify index setup
    assert days.index.name == "Day"
    assert roster.index.name is None  # Default index is names


def test_clear_schedule_modes():
    """Test clearing specific duties vs clearing everything."""
    # Setup a roster with mixed data
    df = pd.DataFrame({"D1": ["AM", "X"], "D2": ["24H", ""]}, index=["A", "B"])

    # 1. Clear Duties Only (Keep X)
    res1 = logic.clear_schedule(df, clear_constraints=False)
    assert res1.at["A", "D1"] == ""  # AM cleared
    assert res1.at["B", "D1"] == "X"  # X kept
    assert res1.at["A", "D2"] == ""  # 24H cleared

    # 2. Clear All
    res2 = logic.clear_schedule(df, clear_constraints=True)
    assert res2.at["B", "D1"] == ""  # X also cleared


def test_calculate_stats_multipliers(default_config):
    """Exhaustive test of point scoring logic."""
    # Use standard generate to get correct D-column format
    roster, days = logic.generate_empty_schedule(2025, 1, ["TestUser"])

    # Update config to match roster personnel (Fix for failing test)
    default_config.personnel = ["TestUser"]

    # Configure Points
    pts = default_config.points
    pts.AM = 1.0
    pts.ph_multiplier = 2.0
    pts.weekend_multiplier = 1.5

    # Case A: PH (Multiplier)
    pts.ph_is_multiplier = True
    days.at[1, "Is_PH"] = True
    days.at[1, "Is_Weekend"] = False

    # Case B: Weekend (Addition)
    pts.weekend_is_multiplier = False
    days.at[2, "Is_PH"] = False
    days.at[2, "Is_Weekend"] = True

    # Assign Duties
    # NOTE: Must use "D1", "D2" keys as per logic.generate_empty_schedule
    roster.at["TestUser", "D1"] = "AM"
    roster.at["TestUser", "D2"] = "AM"

    stats = logic.calculate_stats(roster, days, default_config, {})
    user_stats = stats.iloc[0]

    # Calculation:
    # D1 (PH *): 1.0 * 2.0 = 2.0
    # D2 (Wknd +): 1.0 + 1.5 = 2.5
    # Total = 4.5
    assert user_stats["Month Pts"] == 4.5


def test_prepare_solver_request_parsing(default_config):
    """Test converting dataframe to solver request object."""
    roster, days = logic.generate_empty_schedule(2025, 1, default_config.personnel)
    p1 = default_config.personnel[0]

    roster.at[p1, "D5"] = "AM"
    days.at[10, "Active"] = False
    days.at[5, "Mode"] = "SHIFT"

    req = logic.prepare_solver_request(2025, 1, roster, days, default_config)

    assert req.year == 2025
    assert req.month == 1
    assert req.fixed_assignments[(p1, 5)] == "AM"
    assert 10 in req.inactive_days
    assert req.day_modes[5] == "SHIFT"
