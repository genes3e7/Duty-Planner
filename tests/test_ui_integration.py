"""
tests/test_ui_integration.py

Focus: Integration testing of the Streamlit UI.
Verifies:
1. Widget interactions update Session State.
2. Page navigation works.
3. Settings modifications persist to Config.
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

    # The rules page has tabs. Constraints are in the first tab ("Configuration").
    # We look for "AM Staff" (label standardized in recent UI update)

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

    # Find "Is Multiplier?" checkbox for PH.
    # Since labels are generic ("Is Multiplier?"), we use the Key for robust lookup.

    ph_checkbox = None
    for widget in at.checkbox:
        if widget.key == "pt_bool_ph_is_multiplier":
            ph_checkbox = widget
            break

    assert ph_checkbox is not None, "Could not find PH multiplier checkbox (key='pt_bool_ph_is_multiplier')"

    # Toggle off
    ph_checkbox.set_value(False).run(timeout=30)

    assert at.session_state.app_config.points.ph_is_multiplier is False


def test_planner_toggle_wknd_ph_active():
    """
    Test that the 'Toggle Wknd/PH Active' button correctly flips the Active
    status for both weekends and public holidays in the day configuration DataFrame.
    """
    at = AppTest.from_file("streamlit_app.py").run(timeout=30)

    # Ensure we are on the Planner page (default, but explicit is better)
    at.sidebar.radio("navigation_radio").set_value("Planner").run(timeout=30)

    # Find the newly added toggle button
    toggle_btn = None
    for btn in at.button:
        if btn.label == "Toggle Wknd/PH Active":
            toggle_btn = btn
            break

    assert toggle_btn is not None, "Could not find 'Toggle Wknd/PH Active' button"

    # 1. Verify Initial State
    initial_df = at.session_state.day_config_df
    target_mask = initial_df["Is_Weekend"].fillna(False) | initial_df["Is_PH"].fillna(False)

    # Handle the edge case where a generated month has no weekends or PHs
    if not target_mask.any():
        # Click the button anyway to verify it handles an empty mask gracefully
        toggle_btn.click().run(timeout=30)
        assert at.session_state.day_config_df.equals(initial_df), (
            "Day config should remain unchanged if no weekend or PH targets exist."
        )
        return  # Skip the rest of the assertions

    assert initial_df.loc[target_mask, "Active"].all(), "Expected targeted days to initially be Active."

    # 2. Click Toggle (Should turn them OFF)
    toggle_btn.click().run(timeout=30)

    toggled_off_df = at.session_state.day_config_df
    assert (~toggled_off_df.loc[target_mask, "Active"]).all(), "Expected all targeted days to be toggled inactive."

    # Ensure normal weekdays are NOT affected
    normal_mask = ~target_mask
    if normal_mask.any():
        assert toggled_off_df.loc[normal_mask, "Active"].all(), "Normal weekdays should remain active."

    # 3. Click Toggle Again (Should turn them back ON)
    toggle_btn.click().run(timeout=30)

    toggled_on_df = at.session_state.day_config_df
    assert toggled_on_df.loc[target_mask, "Active"].all(), "Expected targeted days to be toggled back to active."
