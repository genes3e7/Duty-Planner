"""
app/ui/sidebar.py

Handles the sidebar navigation and configuration inputs.
"""

import datetime
import logging

import streamlit as st

from app.core.data import DataManager
from app.models.config import AppConfig

logger = logging.getLogger(__name__)


def render_sidebar() -> str:
    """
    Renders the sidebar and returns the selected navigation page.
    """
    st.sidebar.title("Duty Planner")

    # 1. Navigation
    # Added key for testing stability
    page = st.sidebar.radio("Navigation", ["Planner", "Settings"], key="navigation_radio")

    st.sidebar.divider()

    # 2. Configuration Loading
    st.sidebar.subheader("Configuration")

    # Check for existing config in session, else load
    if "app_config" not in st.session_state:
        st.session_state.app_config = DataManager.load_config()

    config: AppConfig = st.session_state.app_config

    # Date Selection
    # Safely handle default date construction
    try:
        default_date = datetime.date(config.year, config.month, 1)
    except ValueError:
        default_date = datetime.date.today()

    col1, col2 = st.sidebar.columns(2)
    with col1:
        sel_year = st.number_input("Year", min_value=2000, max_value=2100, value=default_date.year)
    with col2:
        sel_month = st.number_input("Month", min_value=1, max_value=12, value=default_date.month)

    if sel_year != config.year or sel_month != config.month:
        config.year = sel_year
        config.month = sel_month
        # Invalidate planner cache if date changes
        st.session_state.loaded_date = None

    # Actions
    if st.sidebar.button("💾 Save Configuration"):
        if DataManager.save_config(config):
            st.toast("Configuration saved!", icon="✅")
        else:
            st.error("Failed to save configuration.")

    st.sidebar.divider()

    # 3. Import History (Stubbed)
    st.sidebar.subheader("Import Previous")
    uploaded_file = st.sidebar.file_uploader("Upload Previous Roster (.xlsx)", type=["xlsx"])

    if uploaded_file:
        # Stub logic for now - typically you'd save to temp and load
        st.info("Import feature enabled but requires backend implementation to handle file stream.")
        # Logic to actually process would go here using DataManager.load_previous_balance

    return page
