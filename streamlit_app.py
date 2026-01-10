"""
streamlit_app.py

The main entry point for the Duty Planner Streamlit application.

This script:
1. Initializes the global logging configuration.
2. Sets up the Streamlit page configuration (title, layout).
3. Loads the application configuration and data.
4. Renders the main sidebar and orchestrates the UI page selection.
"""

import streamlit as st

from app import constants as C
from app.core.data import DataManager
from app.ui.planner import render_planner
from app.ui.settings import render_settings
from app.ui.sidebar import render_sidebar
from app.utils.logger import setup_logger

# 1. LINKING THE LOGGER
# Initialize the logger for the 'app' namespace.
# All modules under 'app.' will inherit this configuration.
logger = setup_logger()


def main():
    """
    Main application execution function.
    Sets up the page and routes the user to the selected view (Planner or Settings).
    """
    # 2. Page Configuration
    st.set_page_config(
        page_title=C.APP_TITLE,
        page_icon=C.APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )

    logger.info("Application started. Loading configuration...")

    # 3. Load Data & Config
    # We load config here to pass it down, ensuring a single source of truth
    # We use session state to ensure config persists across re-runs
    if "config" not in st.session_state:
        st.session_state.config = DataManager.load_config()

    config = st.session_state.config

    # 4. Render Sidebar
    # The sidebar handles actions that affect global state (like saving config)
    # It returns the current navigation selection (e.g., "Planner" or "Settings")
    selected_page = render_sidebar(config)

    # 5. Route to Main Content
    logger.debug(f"User navigated to page: {selected_page}")

    if selected_page == "Planner":
        # Pass the config (which now contains the selected date from sidebar)
        render_planner(config)
    elif selected_page == "Settings":
        render_settings(config)
    else:
        st.error(f"Unknown page selection: {selected_page}")
        logger.error(f"Encountered unknown page selection: {selected_page}")


if __name__ == "__main__":
    main()
