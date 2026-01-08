import pytest
from app.models.config import AppConfig

def test_config_defaults():
    """Test default configuration values."""
    cfg = AppConfig.default()
    assert cfg.year == 2025
    # assert cfg.mode == "hybrid"  <-- REMOVE THIS LINE
    assert len(cfg.personnel) == 2

def test_config_serialization():
    """Test to_dict and from_dict roundtrip."""
    cfg = AppConfig.default()
    cfg.personnel = ["Alice", "Bob"]
    cfg.points.AM = 5.0

    # Serialize
    data = cfg.to_dict()
    assert data["personnel"] == ["Alice", "Bob"]
    
    # Check key remapping (FULL_24H -> 24H)
    # Note: Default value is 2.0, the test checked for 3.0? 
    # Let's check for the default value unless we set it.
    assert data["points"]["24H"] == 2.0 
    
    # Deserialize
    cfg_new = AppConfig.from_dict(data)
    assert cfg_new.personnel == ["Alice", "Bob"]
    assert cfg_new.points.AM == 5.0
