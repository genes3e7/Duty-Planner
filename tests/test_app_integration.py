"""
tests/test_app_integration.py
"""

from streamlit.testing.v1 import AppTest


def test_settings_personnel_modification():
    """Test that changing settings updates the config object."""
    at = AppTest.from_file("streamlit_app.py").run()

    # Navigate to Settings
    at.sidebar.radio("navigation_radio").set_value("Settings").run()

    # Find personnel text_area by label
    personnel_area = None
    for widget in at.text_area:
        # Streamlit sometimes has empty labels in tests or full matches
        if "Names" in widget.label:
            personnel_area = widget
            break

    assert personnel_area is not None, "Could not find personnel text_area"

    personnel_area.input("Alice, Bob, Charlie").run()

    # Verify session state update
    # Note: Streamlit tests run in a sandbox; we check the widget value or session state if accessible
    assert "Alice" in at.session_state.app_config.personnel
    assert "Bob" in at.session_state.app_config.personnel
    assert len(at.session_state.app_config.personnel) == 3


def test_settings_shift_constraints_logic():
    """
    Test the critical logic where updating a number input
    must correctly update the dictionary in Pydantic.
    """
    at = AppTest.from_file("streamlit_app.py").run()
    at.sidebar.radio("navigation_radio").set_value("Settings").run()

    # The settings page has 3 number inputs for constraints: AM, PM, 24H
    # We need to identify them. Usually they are in order of creation.
    # Settings.py creates: AM (c1), PM (c2), 24H (c3)

    # Let's target the "AM Staff Needed" input.
    # We iterate to find the one with the correct label.
    am_input = None
    for widget in at.number_input:
        if "AM Staff Needed" in widget.label:
            am_input = widget
            break

    assert am_input is not None, "Could not find 'AM Staff Needed' widget"

    # Set value to 5
    am_input.set_value(5).run()

    # Verify Config Update
    # This proves the dict replacement logic {**old, "AM": 5} worked
    assert at.session_state.app_config.constraints.personnel_needed_per_shift["AM"] == 5

    # Verify others remained untouched (default is 1)
    assert at.session_state.app_config.constraints.personnel_needed_per_shift["PM"] == 1


def test_settings_point_multipliers():
    """Test toggling a boolean checkbox for multipliers."""
    at = AppTest.from_file("streamlit_app.py").run()
    at.sidebar.radio("navigation_radio").set_value("Settings").run()

    # Find "Is Multiplier? (PH)" checkbox
    ph_checkbox = None
    for widget in at.checkbox:
        if "Is Multiplier? (PH)" in widget.label:
            ph_checkbox = widget
            break

    assert ph_checkbox is not None

    # Toggle off
    ph_checkbox.set_value(False).run()

    assert at.session_state.app_config.points.ph_is_multiplier is False
