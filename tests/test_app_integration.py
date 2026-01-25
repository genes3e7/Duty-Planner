"""
tests/test_app_integration.py
"""

from streamlit.testing.v1 import AppTest


def test_settings_personnel_modification():
    """Test that changing settings updates the config object."""
    at = AppTest.from_file("streamlit_app.py").run(timeout=30)

    # Navigate to Settings
    at.sidebar.radio("navigation_radio").set_value("Settings").run(timeout=30)

    # Find personnel text_area by label
    personnel_area = None
    for widget in at.text_area:
        if "Names" in widget.label:
            personnel_area = widget
            break

    assert personnel_area is not None, "Could not find personnel text_area"

    personnel_area.input("Alice, Bob, Charlie").run(timeout=30)

    # Verify session state update
    assert "Alice" in at.session_state.app_config.personnel
    assert "Bob" in at.session_state.app_config.personnel
    assert len(at.session_state.app_config.personnel) == 3


def test_rules_shift_constraints_logic():
    """
    Test that updating constraints (now in Rules page) correctly updates config.
    """
    at = AppTest.from_file("streamlit_app.py").run(timeout=30)

    # FIX: Navigate to "Rules" instead of "Settings"
    at.sidebar.radio("navigation_radio").set_value("Rules").run(timeout=30)

    # Updated Label: "AM Staff" (was "AM Needed" / "AM Staff Needed")
    am_input = None
    for widget in at.number_input:
        if "AM Staff" in widget.label:
            am_input = widget
            break

    assert am_input is not None, "Could not find 'AM Staff' widget on Rules page"

    # Set value to 5
    am_input.set_value(5).run(timeout=30)

    # Verify Config Update
    assert at.session_state.app_config.constraints.personnel_needed_per_shift["AM"] == 5
    assert at.session_state.app_config.constraints.personnel_needed_per_shift["PM"] == 1


def test_settings_point_multipliers():
    """Test toggling a boolean checkbox for multipliers in Settings."""
    at = AppTest.from_file("streamlit_app.py").run(timeout=30)
    at.sidebar.radio("navigation_radio").set_value("Settings").run(timeout=30)

    # Search for specific key to be robust against label changes
    ph_checkbox = None
    for widget in at.checkbox:
        if widget.key == "pt_bool_ph_is_multiplier":
            ph_checkbox = widget
            break

    assert ph_checkbox is not None, "Could not find PH multiplier checkbox"

    # Toggle off
    ph_checkbox.set_value(False).run(timeout=30)

    assert at.session_state.app_config.points.ph_is_multiplier is False
