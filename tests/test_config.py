from app.constants import ShiftType
from app.models.config import AppConfig, PointsConfig


def test_config_defaults():
    """Test default configuration values."""
    cfg = AppConfig.default()
    assert cfg.year == 2025
    assert cfg.mode == "hybrid"
    assert cfg.constraints.personnel_needed_per_shift["AM"] == 1


def test_points_config_lookup():
    """Test that points are correctly retrieved by shift type."""
    pts = PointsConfig(AM=1.5, PM=2.0, FULL_24H=5.0)

    assert pts.get_by_type(ShiftType.AM) == 1.5
    assert pts.get_by_type(ShiftType.PM) == 2.0
    assert pts.get_by_type(ShiftType.FULL_24H) == 5.0
    assert pts.get_by_type("INVALID") == 0.0


def test_config_serialization():
    """Test to_dict and from_dict roundtrip."""
    cfg = AppConfig.default()
    cfg.personnel = ["Alice", "Bob"]
    cfg.points.AM = 5.0

    # Serialize
    data = cfg.to_dict()
    assert data["personnel"] == ["Alice", "Bob"]
    # Check key remapping (FULL_24H -> 24H)
    assert data["points"]["24H"] == 3.0

    # Deserialize
    new_cfg = AppConfig.from_dict(data)
    assert new_cfg.personnel == ["Alice", "Bob"]
    assert new_cfg.points.AM == 5.0
    # Ensure remapped keys came back correctly
    assert new_cfg.points.FULL_24H == 3.0
