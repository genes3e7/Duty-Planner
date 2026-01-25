"""
tests/test_points_system.py

Comprehensive tests for the Point Scoring System.
Verifies interactions between Base Points, Multipliers, Adders, and Team Suffixes.
"""

import datetime

import pytest

from app.models.config import AppConfig

# --- Fixtures ---


@pytest.fixture
def config():
    """Returns a fresh AppConfig with known defaults."""
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
    """A Saturday."""
    return datetime.date(2025, 1, 4)


@pytest.fixture
def mon_date():
    """A Monday."""
    return datetime.date(2025, 1, 6)


@pytest.fixture
def ph_list():
    """List containing a Monday PH."""
    return [datetime.date(2025, 1, 6)]


# --- Base Point Tests ---


def test_base_points_retrieval(config, mon_date):
    """Test that base points are correctly retrieved for all types."""
    assert config.points.calculate_score(mon_date, "AM") == 10
    assert config.points.calculate_score(mon_date, "PM") == 20
    assert config.points.calculate_score(mon_date, "24H") == 30
    assert config.points.calculate_score(mon_date, "S/B") == 5


def test_team_suffix_inheritance(config, mon_date):
    """Test that _2, _3 suffixes inherit base points correctly."""
    assert config.points.calculate_score(mon_date, "AM_2") == 10
    assert config.points.calculate_score(mon_date, "PM_99") == 20
    assert config.points.calculate_score(mon_date, "S/B_2") == 5


# --- Multiplier Logic Tests ---


def test_weekend_multiplier(config, sat_date):
    """Test standard x2 Multiplier on Weekend."""
    config.points.weekend_multiplier = 2.0
    config.points.weekend_is_multiplier = True

    # AM: 10 * 2 = 20
    assert config.points.calculate_score(sat_date, "AM") == 20
    # S/B: 5 * 2 = 10 (S/B should be affected by multipliers!)
    assert config.points.calculate_score(sat_date, "S/B") == 10


def test_weekend_adder(config, sat_date):
    """Test +5 Adder on Weekend."""
    config.points.weekend_multiplier = 5.0
    config.points.weekend_is_multiplier = False

    # AM: 10 + 5 = 15
    assert config.points.calculate_score(sat_date, "AM") == 15
    # S/B: 5 + 5 = 10
    assert config.points.calculate_score(sat_date, "S/B") == 10


def test_ph_multiplier(config, mon_date, ph_list):
    """Test PH Multiplier logic."""
    config.points.ph_multiplier = 3.0
    config.points.ph_is_multiplier = True

    # Monday is PH
    assert config.points.calculate_score(mon_date, "AM", holidays_obj=ph_list) == 30  # 10*3
    assert config.points.calculate_score(mon_date, "S/B", holidays_obj=ph_list) == 15  # 5*3


# --- CRITICAL BUG TEST: Zero Points ---


def test_zero_base_points_neutral(config, mon_date):
    """If S/B is set to 0, it should be 0 on a normal day."""
    config.points.SB = 0.0
    assert config.points.calculate_score(mon_date, "S/B") == 0


def test_zero_base_points_with_multiplier(config, sat_date):
    """
    If S/B is 0, Multiplier (x2) should result in 0.
    0 * 2 = 0.
    """
    config.points.SB = 0.0
    config.points.weekend_multiplier = 2.0
    config.points.weekend_is_multiplier = True

    assert config.points.calculate_score(sat_date, "S/B") == 0


def test_zero_base_points_with_adder(config, sat_date):
    """
    If S/B is 0, Adder (+5) should strictly result in 0.
    Rationale: If a duty is worth 0, it shouldn't get bonus points.
    """
    config.points.SB = 0.0
    config.points.weekend_multiplier = 5.0
    config.points.weekend_is_multiplier = False  # +5 Adder

    assert config.points.calculate_score(sat_date, "S/B") == 0


def test_sb_team_zero_points(config, sat_date):
    """Test S/B_2 inherits the 0.0 correctly."""
    config.points.SB = 0.0
    config.points.weekend_multiplier = 2.0

    assert config.points.calculate_score(sat_date, "S/B_2") == 0


# --- CRITICAL BUG TEST: Team Shift on Public Holiday ---


def test_team_shift_on_public_holiday(config_ph):
    """
    Verifies that 24H_2 correctly triggers PH multipliers.
    Bug Fix Verification: Previously 24H_2 was not recognized as 24H
    and missed the 2x multiplier.
    """
    ph_date = datetime.date(2026, 2, 18)
    holidays = {ph_date}

    # Base 100 * 2.0 = 200
    score = config_ph.points.calculate_score(ph_date, "24H_2", scale=1, holidays_obj=holidays)

    assert score == 200
