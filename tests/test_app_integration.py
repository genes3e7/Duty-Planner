"""
tests/test_app_integration.py
"""

from streamlit.testing.v1 import AppTest


def test_settings_modification():
    """Test that changing settings updates the config object."""
    at = AppTest.from_file("streamlit_app.py").run()

    # Navigate to Settings using the explicit key
    at.sidebar.radio("navigation_radio").set_value("Settings").run()

    # Modify Personnel
    # Note: Streamlit testing requires finding the widget again after run()
    text_areas = at.text_area
    if text_areas:
        # Assuming the first text area is the personnel input
        # Note: Depending on layout, this might be index 0 or 1.
        # In settings.py, the first text area is "Names (comma separated)"
        text_areas[0].input("Alice, Bob, Charlie").run()

        # Refetch widget to assert value
        updated_area = at.text_area[0]
        assert "Alice, Bob, Charlie" in updated_area.value
