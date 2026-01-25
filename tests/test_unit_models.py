"""
tests/test_unit_models.py

Focus: Unit tests for Data Models (Config) and Domain Logic (Points).
Verifies:
1. Pydantic validation (Constraints, Types).
2. Point calculation logic (Multipliers, Adders, Inheritance).
"""

import datetime

import pytest
from dateutil.relativedelta import relativedelta
from pydantic import ValidationError

from app.models.config import AppConfig, ConstraintsConfig, PointsConfig

# --- Fixtures (from test_points_system.py) ---


@pytest.fixture
def config_defaults():
    """Returns a fresh AppConfig with known defaults for point testing."""
    cfg = AppConfig.default()
    # Reset multipliers to 1.0/False (neutral state)
    cfg.points.weekend_multiplier = 1.0
    cfg.points.weekend_is_multiplier = True
    cfg.points.ph_multiplier = 1.0
    cfg.points.ph_is_multiplier = True
    # Reset base points
    cfg.points.AM = 10.0
    cfg.points.PM = 20.0
    cfg.points.FULL_24H = 30.0
    cfg.points.SB = 5.0
    return cfg


@pytest.fixture
def config_ph():
    """Config with PH multiplier x2.0 active."""
    cfg = AppConfig.default()
    cfg.points.FULL_24H = 100.0
    cfg.points.ph_multiplier = 2.0
    cfg.points.ph_is_multiplier = True
    return cfg


@pytest.fixture
def sat_date():
    return datetime.date(2025, 1, 4)


@pytest.fixture
def mon_date():
    return datetime.date(2025, 1, 6)


@pytest.fixture
def ph_list():
    return [datetime.date(2025, 1, 6)]


# --- Config Validation Tests (from test_config.py) ---


def test_app_config_defaults():
    """Test that default config generates valid structure with dynamic next-month date."""
    cfg = AppConfig.default()
    expected = datetime.date.today() + relativedelta(months=1)
    assert cfg.year == expected.year
    assert cfg.month == expected.month
    assert len(cfg.personnel) == 20


def test_validation_year_month():
    """Test validation for year and month ranges."""
    AppConfig(year=2025, month=12)  # Valid
    with pytest.raises(ValidationError):
        AppConfig(year=2025, month=13)
    with pytest.raises(ValidationError):
        AppConfig(year=1999, month=1)


def test_validation_negative_values():
    """Test that negative requirements/points raise errors."""
    with pytest.raises(ValidationError):
        ConstraintsConfig(personnel_needed_per_shift={"AM": -1})
    with pytest.raises(ValidationError):
        PointsConfig(AM=-1.0)


def test_points_config_get_by_type():
    """Test the helper method get_by_type in PointsConfig."""
    pc = PointsConfig(AM=1.5, PM=2.0, FULL_24H=5.0, SB=0.5)
    assert pc.get_by_type("AM") == 1.5
    assert pc.get_by_type("24H") == 5.0
    # Test Suffix Handling
    assert pc.get_by_type("AM_2") == 1.5

    with pytest.raises(ValueError):
        pc.get_by_type("UNKNOWN")


# --- Points System Tests (from test_points_system.py) ---


def test_base_points_retrieval(config_defaults, mon_date):
    """Test that base points are correctly retrieved for all types."""
    pts = config_defaults.points
    assert pts.calculate_score(mon_date, "AM") == 10
    assert pts.calculate_score(mon_date, "PM") == 20
    assert pts.calculate_score(mon_date, "24H") == 30
    assert pts.calculate_score(mon_date, "S/B") == 5


def test_team_suffix_inheritance(config_defaults, mon_date):
    """Test that _2, _3 suffixes inherit base points correctly."""
    pts = config_defaults.points
    assert pts.calculate_score(mon_date, "AM_2") == 10
    assert pts.calculate_score(mon_date, "S/B_2") == 5


def test_weekend_multiplier_logic(config_defaults, sat_date):
    """Test standard x2 Multiplier on Weekend."""
    pts = config_defaults.points
    pts.weekend_multiplier = 2.0
    pts.weekend_is_multiplier = True

    # AM: 10 * 2 = 20
    assert pts.calculate_score(sat_date, "AM") == 20


def test_ph_multiplier_logic(config_defaults, mon_date, ph_list):
    """Test PH Multiplier logic."""
    pts = config_defaults.points
    pts.ph_multiplier = 3.0
    pts.ph_is_multiplier = True

    # Monday is PH: 10 * 3 = 30
    assert pts.calculate_score(mon_date, "AM", holidays_obj=ph_list) == 30


def test_zero_points_logic(config_defaults, sat_date):
    """If Base Points are 0, Multipliers should still result in 0."""
    pts = config_defaults.points
    pts.SB = 0.0
    pts.weekend_multiplier = 2.0

    assert pts.calculate_score(sat_date, "S/B") == 0
    assert pts.calculate_score(sat_date, "S/B_2") == 0


def test_team_shift_on_public_holiday(config_ph):
    """
    Verifies that 24H_2 correctly triggers PH multipliers.
    Bug Fix Verification: 24H_2 must inherit 24H logic.
    """
    ph_date = datetime.date(2026, 2, 18)
    holidays = {ph_date}
    # Base 100 * 2.0 = 200
    score = config_ph.points.calculate_score(ph_date, "24H_2", scale=1, holidays_obj=holidays)
    assert score == 200
