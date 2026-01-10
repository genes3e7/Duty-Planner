"""
tests/test_config.py

Tests for configuration models and validation logic.
Verifies that defensive validators prevent invalid configurations.
"""

import pytest
from pydantic import ValidationError

from app.models.config import AppConfig, ConstraintsConfig, PointsConfig


def test_app_config_defaults():
    """Test that default config generates valid structure."""
    cfg = AppConfig.default()
    assert cfg.year == 2025
    assert len(cfg.personnel) == 20
    assert cfg.constraints.standby_per_day == 1


def test_validation_year_month():
    """Test validation for year and month ranges."""
    # Valid
    AppConfig(year=2025, month=12)

    # Invalid Month
    with pytest.raises(ValidationError):
        AppConfig(year=2025, month=13)

    with pytest.raises(ValidationError):
        AppConfig(year=2025, month=0)

    # Invalid Year
    with pytest.raises(ValidationError):
        AppConfig(year=1999, month=1)


def test_validation_negative_needs():
    """Test that negative manpower requirements raise error."""
    with pytest.raises(ValidationError):
        ConstraintsConfig(personnel_needed_per_shift={"AM": -1})


def test_validation_negative_points():
    """Test that negative points raise error."""
    with pytest.raises(ValidationError):
        PointsConfig(AM=-1.0)

    with pytest.raises(ValidationError):
        PointsConfig(weekend_multiplier=-0.5)


def test_points_config_logic():
    """Test the helper method get_by_type in PointsConfig."""
    pc = PointsConfig(AM=1.5, PM=2.0, FULL_24H=5.0, SB=0.5)

    assert pc.get_by_type("AM") == 1.5
    assert pc.get_by_type("PM") == 2.0
    assert pc.get_by_type("24H") == 5.0
    assert pc.get_by_type("S/B") == 0.5

    with pytest.raises(ValueError):
        pc.get_by_type("UNKNOWN")
