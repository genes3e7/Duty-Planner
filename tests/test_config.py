import pytest
from pydantic import ValidationError

from app.models.config import AppConfig, PointsConfig


def test_config_defaults():
    """Test that default configuration initializes with safe, expected values."""
    cfg = AppConfig.default()
    assert cfg.year == 2025
    assert cfg.month == 1
    # Check 20 fake names are generated
    assert len(cfg.personnel) == 20
    assert cfg.personnel[0] == "Staff 01"

    # Check constraint defaults
    assert cfg.constraints.personnel_needed_per_shift["AM"] == 1
    assert cfg.constraints.standby_per_day == 1


def test_points_config_logic():
    """Test the helper method get_by_type in PointsConfig."""
    pc = PointsConfig(AM=1.5, PM=2.0, FULL_24H=5.0, SB=0.5)

    # Test valid keys
    assert pc.get_by_type("AM") == 1.5
    assert pc.get_by_type("PM") == 2.0
    assert pc.get_by_type("24H") == 5.0
    assert pc.get_by_type("S/B") == 0.5

    # Test invalid key raises ValueError
    with pytest.raises(ValueError, match="Unknown shift type"):
        pc.get_by_type("INVALID_SHIFT")


def test_config_serialization_roundtrip():
    """Test that we can serialize to dict and back without data loss."""
    cfg = AppConfig.default()
    cfg.personnel = ["Alice", "Bob"]
    cfg.points.AM = 99.0

    # 1. Serialize (ensure aliasing works for 24H)
    data = cfg.to_dict()
    assert data["personnel"] == ["Alice", "Bob"]
    assert data["points"]["24H"] == 2.0  # Default value

    # 2. Deserialize
    cfg_new = AppConfig.from_dict(data)
    assert cfg_new.personnel == ["Alice", "Bob"]
    assert cfg_new.points.AM == 99.0
    assert cfg_new.points.FULL_24H == 2.0


def test_pydantic_validation():
    """Test that invalid types raise validation errors."""
    with pytest.raises(ValidationError):
        # Year must be int
        AppConfig(year="invalid_year")
