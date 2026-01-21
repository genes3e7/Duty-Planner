"""
streamlit_app.py

Main entry point for the Streamlit application.
Orchestrates the UI layout and page navigation.
"""

import streamlit as st

from app import constants as C
from app.ui.planner import render_planner
from app.ui.rules import render_rules
from app.ui.settings import render_settings
from app.ui.sidebar import render_sidebar
from app.utils.logger import setup_logger

# Initialize Logger
logger = setup_logger()


def main():
    """
    Main app execution flow.
    """
    st.set_page_config(
        page_title=C.APP_TITLE,
        page_icon="🗓️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Render Sidebar & Get Navigation Choice
    page = render_sidebar()

    # Retrieve Config from Session State (loaded in sidebar)
    if "app_config" in st.session_state:
        config = st.session_state.app_config

        if page == "Planner":
            render_planner(config)
        elif page == "Rules":
            render_rules(config)
        elif page == "Settings":
            render_settings(config)
    else:
        st.error("Failed to load configuration.")


if __name__ == "__main__":
    main()
