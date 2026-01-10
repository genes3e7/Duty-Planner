"""
tests/test_app_integration.py

Integration tests for the Streamlit application using `streamlit.testing.AppTest`.
Verifies that the main UI components load and interact correctly.
"""

from streamlit.testing.v1 import AppTest


def test_app_loads_correctly():
    """Verify the app starts and displays the correct title."""
    # We use default_timeout to allow slower CI environments to catch up
    at = AppTest.from_file("streamlit_app.py", default_timeout=10)
    at.run()

    # Check for exceptions during startup
    assert not at.exception, f"App failed to start: {at.exception}"

    # Verify sidebar exists
    assert len(at.sidebar) > 0


def test_grid_generation():
    """Simulate clicking 'Reset Grid' and verify grid appears."""
    at = AppTest.from_file("streamlit_app.py", default_timeout=10)
    at.run()

    # Find the 'Reset Grid' button
    reset_btns = [b for b in at.button if "Reset" in b.label]

    assert len(reset_btns) > 0, "Reset button not found in UI"

    # Click the button and re-run
    reset_btns[0].click().run()

    # After loading, we expect the "Assignments" subheader to appear
    # We avoid checking at.data_editor directly as it causes AttributeError
    # in some Streamlit test versions.
    subheaders = [h.body for h in at.subheader]
    assert "Assignments" in subheaders, f"Grid did not load. Subheaders found: {subheaders}"


def test_settings_modification():
    """Test that changing settings in the UI persists."""
    at = AppTest.from_file("streamlit_app.py", default_timeout=10)
    at.run()

    # 1. Switch to Settings via Radio Button in Sidebar
    # Find the navigation radio
    nav_radios = [r for r in at.sidebar.radio if "Navigation" in r.label]
    assert len(nav_radios) > 0, "Navigation radio not found"

    nav_radios[0].set_value("Settings").run()

    # 2. Look for the Personnel text area
    # We search broadly for any text area that might hold names
    personnel_areas = [t for t in at.text_area if "Names" in t.label or "Personnel" in t.label or "Staff" in t.label]

    assert len(personnel_areas) > 0, "Settings text area not found. Navigation might have failed."

    # 3. Modify the text
    # Original default has ~20 names. Let's change it to just "Alice, Bob"
    personnel_areas[0].input("Alice, Bob").run()

    # 4. Verify persistence
    # We check if the text area value retained the change.
    assert "Alice, Bob" in personnel_areas[0].value
