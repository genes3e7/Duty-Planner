"""
app/ui/settings.py

Handles the configuration settings interface.
Allows modifying personnel list, shift constraints, and point values.
"""

import streamlit as st

from app.models.config import AppConfig


def render_settings(config: AppConfig):
    """
    Renders the settings page.

    Args:
        config (AppConfig): The application configuration object to edit.
    """
    st.title("⚙️ Settings")

    # 1. Personnel Management
    st.subheader("Personnel")
    st.caption("Manage the list of staff available for duties.")

    current_names = ", ".join(config.personnel)
    new_names_str = st.text_area("Names (comma separated)", value=current_names, height=100)

    # Update config immediately on change
    if new_names_str != current_names:
        new_list = [n.strip() for n in new_names_str.split(",") if n.strip()]
        config.personnel = new_list
        # We don't rerun here to allow bulk edits, but data binds to the object reference

    st.markdown("---")

    # 2. Shift Constraints
    st.subheader("Shift Constraints")

    c1, c2, c3 = st.columns(3)
    with c1:
        config.constraints.personnel_needed_per_shift["AM"] = st.number_input(
            "AM Staff Needed", min_value=0, value=config.constraints.personnel_needed_per_shift.get("AM", 1)
        )
    with c2:
        config.constraints.personnel_needed_per_shift["PM"] = st.number_input(
            "PM Staff Needed", min_value=0, value=config.constraints.personnel_needed_per_shift.get("PM", 1)
        )
    with c3:
        config.constraints.personnel_needed_per_shift["24H"] = st.number_input(
            "24H Staff Needed", min_value=0, value=config.constraints.personnel_needed_per_shift.get("24H", 1)
        )

    st.markdown("---")

    # 3. Point Values
    st.subheader("Point Scoring Rules")

    with st.expander("Base Points"):
        p1, p2, p3, p4 = st.columns(4)
        with p1:
            config.points.AM = st.number_input("AM Pts", value=config.points.AM)
        with p2:
            config.points.PM = st.number_input("PM Pts", value=config.points.PM)
        with p3:
            config.points.FULL_24H = st.number_input("24H Pts", value=config.points.FULL_24H)
        with p4:
            config.points.SB = st.number_input("Standby Pts", value=config.points.SB)

    with st.expander("Multipliers"):
        m1, m2 = st.columns(2)
        with m1:
            config.points.ph_multiplier = st.number_input("PH Multiplier", value=config.points.ph_multiplier)
            config.points.weekend_multiplier = st.number_input(
                "Weekend Multiplier", value=config.points.weekend_multiplier
            )
        with m2:
            config.points.ph_is_multiplier = st.checkbox("PH is Multiplier?", value=config.points.ph_is_multiplier)
            config.points.weekend_is_multiplier = st.checkbox(
                "Weekend is Multiplier?", value=config.points.weekend_is_multiplier
            )

    st.info("Settings are applied in memory. Click 'Save Configuration' in the sidebar to persist to disk.")
