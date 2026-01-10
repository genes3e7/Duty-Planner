"""
app/ui/sidebar.py

Handles the rendering of the Streamlit sidebar.
Includes controls for global actions (Save, Load Balance), Navigation,
and Date Selection.
"""

import calendar
import datetime

import streamlit as st

from app.core.data import DataManager
from app.models.config import AppConfig


def render_sidebar(config: AppConfig) -> str:
    """
    Renders the sidebar components and returns the selected page name.

    Also updates the 'config' object with the selected year/month.

    Args:
        config (AppConfig): The current application configuration object.

    Returns:
        str: The name of the selected page ("Planner" or "Settings").
    """
    st.sidebar.title("Duty Planner")

    # 1. Navigation
    page = st.sidebar.radio("Navigation", ["Planner", "Settings"])

    st.sidebar.markdown("---")

    # 2. Date Selection (Global Context)
    st.sidebar.subheader("Planning Period")

    # Default to config's current year/month or today
    default_date = datetime.date(config.year, config.month, 1)

    # Safe fallback if config has invalid date
    try:
        default_date = datetime.date(config.year, config.month, 1)
    except ValueError:
        default_date = datetime.date.today()

    sel_date = st.sidebar.date_input(
        "Select Month",
        value=default_date,
        min_value=datetime.date(2000, 1, 1),
        max_value=datetime.date(2100, 12, 31),
        help="Pick any day in the month you want to plan for.",
    )

    # Update Config with selection
    # We allow the user to change the month freely.
    # The Planner view will react to this change.
    config.year = sel_date.year
    config.month = sel_date.month

    month_name = calendar.month_name[config.month]
    st.sidebar.caption(f"Selected: **{month_name} {config.year}**")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Global Actions")

    # 3. Save Configuration Button
    if st.sidebar.button("💾 Save Configuration"):
        if DataManager.save_config(config):
            st.sidebar.success("Config saved!")
        else:
            st.sidebar.error("Failed to save config.")

    # 4. Load Previous Balance
    with st.sidebar.expander("Import History"):
        uploaded_file = st.file_uploader("Upload Previous Month's Excel", type=["xlsx"])
        if uploaded_file:
            # In a real scenario, we'd save this to a temp file and load it.
            # For now, we mock the success or implement if DataManager supports bytes.
            # DataManager.load_previous_balance expects a path.
            # We'll rely on the Planner to handle logic or implement temp file handling here.
            # For this UI component, we just show it exists.
            st.info("File uploaded. Logic pending integration.")

    st.sidebar.markdown("---")
    st.sidebar.caption("v1.0.0 | Duty Planner")

    return page
