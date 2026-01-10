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
    new_list = [n.strip() for n in new_names_str.split(",") if n.strip()]
    if new_list != config.personnel:
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

    with st.expander("Multipliers", expanded=True):
        st.caption("Multipliers scale the base points (e.g. 2x). If unchecked, the value is added (e.g. +2).")

        # Row 1: Public Holidays & Eves
        st.markdown("**Holidays**")
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            config.points.ph_multiplier = st.number_input("PH Value", value=config.points.ph_multiplier)
        with m2:
            config.points.ph_is_multiplier = st.checkbox("Is Multiplier? (PH)", value=config.points.ph_is_multiplier)
        with m3:
            config.points.ph_eve_multiplier = st.number_input("PH Eve Value", value=config.points.ph_eve_multiplier)
        with m4:
            config.points.ph_eve_is_multiplier = st.checkbox(
                "Is Multiplier? (Eve)", value=config.points.ph_eve_is_multiplier
            )

        st.divider()

        # Row 2: Weekends
        st.markdown("**Weekends**")
        w1, w2 = st.columns(2)
        with w1:
            config.points.weekend_multiplier = st.number_input("Weekend Value", value=config.points.weekend_multiplier)
        with w2:
            config.points.weekend_is_multiplier = st.checkbox(
                "Is Multiplier? (Wknd)", value=config.points.weekend_is_multiplier
            )

        st.divider()

        # Row 3: Friday Split
        st.markdown("**Friday Shifts**")
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            config.points.friday_am_multiplier = st.number_input(
                "Fri AM Value", value=config.points.friday_am_multiplier
            )
        with f2:
            config.points.friday_am_is_multiplier = st.checkbox(
                "Is Multiplier? (Fri AM)", value=config.points.friday_am_is_multiplier
            )
        with f3:
            config.points.friday_pm_multiplier = st.number_input(
                "Fri PM Value", value=config.points.friday_pm_multiplier
            )
        with f4:
            config.points.friday_pm_is_multiplier = st.checkbox(
                "Is Multiplier? (Fri PM)", value=config.points.friday_pm_is_multiplier
            )

    st.info("Settings are applied in memory. Click 'Save Configuration' in the sidebar to persist to disk.")
