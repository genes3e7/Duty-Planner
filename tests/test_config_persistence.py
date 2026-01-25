"""
tests/test_config_persistence.py

Tests the AppConfig model's ability to update itself from dictionary inputs.
Simulates the Session State logic used in the Settings UI.
"""

from app.models.config import AppConfig


def test_simple_value_update():
    """Test updating a top-level field (Personnel)."""
    cfg = AppConfig.default()

    new_data = {"personnel": ["Alice", "Bob"]}
    cfg = cfg.model_copy(update=new_data)

    assert len(cfg.personnel) == 2
    assert "Alice" in cfg.personnel


def test_nested_points_update():
    """
    Test updating nested Point values (simulating the UI logic).
    The UI does: config.points = config.points.model_copy(update=pending_updates)
    """
    cfg = AppConfig.default()

    # 1. Verify Default (SB usually 0 or user defined)
    # Let's force it to 1.0 first to test the change to 0.0
    cfg.points.SB = 1.0
    assert cfg.points.SB == 1.0

    # 2. Simulate User Input: Changing SB to 0.0
    pending_updates = {"SB": 0.0, "AM": 5.0}

    # 3. Apply Update
    cfg.points = cfg.points.model_copy(update=pending_updates)

    # 4. Verify Update Persisted
    assert cfg.points.SB == 0.0
    assert cfg.points.AM == 5.0

    # 5. Verify type consistency (float)
    assert isinstance(cfg.points.SB, float)


def test_alias_update_handling():
    """
    Pydantic sometimes struggles with aliases ("S/B" vs "SB").
    The UI uses field names (keys in the pydantic model), e.g. "SB".
    The Alias is usually for JSON export ("S/B").

    We must ensure updating 'SB' works.
    """
    cfg = AppConfig.default()

    # Update using field name 'SB'
    update_dict = {"SB": 99.0}
    cfg.points = cfg.points.model_copy(update=update_dict)
    assert cfg.points.SB == 99.0


def test_full_roundtrip_logic():
    """
    Simulates the full cycle:
    1. Config -> 2. UI Edit -> 3. Update Config -> 4. Calculate Score
    """
    # 1. Init
    cfg = AppConfig.default()
    cfg.points.SB = 10.0  # Start high

    # 2. UI Logic Simulation
    # User inputs 0.0 for SB in Streamlit
    ui_input_sb = 0.0
    pending_updates = {}

    # Checkbox/Number Input logic
    if ui_input_sb != cfg.points.SB:
        pending_updates["SB"] = ui_input_sb

    # 3. Apply Update
    if pending_updates:
        cfg.points = cfg.points.model_copy(update=pending_updates)

    # 4. Verification
    assert cfg.points.SB == 0.0

    # 5. Calculation Verification
    import datetime

    score = cfg.points.calculate_score(datetime.date(2025, 1, 1), "S/B")
    assert score == 0


def test_settings_reset_behavior():
    """
    Test if we can set a value, then set it back to default/zero.
    """
    cfg = AppConfig.default()

    # Set to 5
    cfg.points = cfg.points.model_copy(update={"SB": 5.0})
    assert cfg.points.SB == 5.0

    # Set to 0
    cfg.points = cfg.points.model_copy(update={"SB": 0.0})
    assert cfg.points.SB == 0.0
