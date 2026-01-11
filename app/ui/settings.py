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
    # De-duplicate names using dict keys to preserve order
    new_list = list(dict.fromkeys([n.strip() for n in new_names_str.split(",") if n.strip()]))

    if new_list != config.personnel:
        if not new_list:
            st.warning("Personnel list cannot be empty. At least one staff member is required.")
        else:
            config.personnel = new_list
        # We don't rerun here to allow bulk edits, but data binds to the object reference

    st.markdown("---")

    # 2. Shift Constraints
    st.subheader("Shift Constraints")

    c1, c2, c3 = st.columns(3)
    shifts = [("AM", c1), ("PM", c2), ("24H", c3)]
    updates = {}

    for shift_name, col in shifts:
        with col:
            val = int(
                st.number_input(
                    f"{shift_name} Staff Needed",
                    min_value=0,
                    value=config.constraints.personnel_needed_per_shift.get(shift_name, 1),
                    step=1,
                    format="%d",
                )
            )
            if val != config.constraints.personnel_needed_per_shift.get(shift_name):
                updates[shift_name] = val

    if updates:
        # Reassign dict to trigger validation
        config.constraints.personnel_needed_per_shift = {
            **config.constraints.personnel_needed_per_shift,
            **updates,
        }

    st.markdown("---")

    # 3. Point Values
    st.subheader("Point Scoring Rules")

    with st.expander("Base Points"):
        p1, p2, p3, p4 = st.columns(4)

        # Use model_copy(update=...) to ensure validation runs on assignment
        # Note: We must update the parent 'config.points' with the new model instance

        with p1:
            val_am = st.number_input("AM Pts", value=config.points.AM)
            if val_am != config.points.AM:
                config.points = config.points.model_copy(update={"AM": val_am})

        with p2:
            val_pm = st.number_input("PM Pts", value=config.points.PM)
            if val_pm != config.points.PM:
                config.points = config.points.model_copy(update={"PM": val_pm})

        with p3:
            val_24h = st.number_input("24H Pts", value=config.points.FULL_24H)
            if val_24h != config.points.FULL_24H:
                config.points = config.points.model_copy(update={"FULL_24H": val_24h})

        with p4:
            val_sb = st.number_input("Standby Pts", value=config.points.SB)
            if val_sb != config.points.SB:
                config.points = config.points.model_copy(update={"SB": val_sb})

    with st.expander("Multipliers", expanded=True):
        st.caption("Multipliers scale the base points (e.g. 2x). If unchecked, the value is added (e.g. +2).")

        # Row 1: Public Holidays & Eves
        st.markdown("**Public Holidays**")
        ph1, ph2 = st.columns(2)
        with ph1:
            val_ph = st.number_input("PH Value", value=config.points.ph_multiplier)
            if val_ph != config.points.ph_multiplier:
                config.points = config.points.model_copy(update={"ph_multiplier": val_ph})
        with ph2:
            val_ph_is_mult = st.checkbox("Is Multiplier? (PH)", value=config.points.ph_is_multiplier)
            if val_ph_is_mult != config.points.ph_is_multiplier:
                config.points = config.points.model_copy(update={"ph_is_multiplier": val_ph_is_mult})

        st.divider()

        # Row 2: Public Holiday Eves (Split)
        st.markdown("**Public Holiday Eves**")
        eve1, eve2, eve3 = st.columns(3)

        with eve1:
            st.markdown("##### AM")
            val_eve_am = st.number_input("Value (Eve AM)", value=config.points.ph_eve_am_multiplier)
            if val_eve_am != config.points.ph_eve_am_multiplier:
                config.points = config.points.model_copy(update={"ph_eve_am_multiplier": val_eve_am})

            val_eve_am_is_mult = st.checkbox("Multiply? (Eve AM)", value=config.points.ph_eve_am_is_multiplier)
            if val_eve_am_is_mult != config.points.ph_eve_am_is_multiplier:
                config.points = config.points.model_copy(update={"ph_eve_am_is_multiplier": val_eve_am_is_mult})

        with eve2:
            st.markdown("##### PM")
            val_eve_pm = st.number_input("Value (Eve PM)", value=config.points.ph_eve_pm_multiplier)
            if val_eve_pm != config.points.ph_eve_pm_multiplier:
                config.points = config.points.model_copy(update={"ph_eve_pm_multiplier": val_eve_pm})

            val_eve_pm_is_mult = st.checkbox("Multiply? (Eve PM)", value=config.points.ph_eve_pm_is_multiplier)
            if val_eve_pm_is_mult != config.points.ph_eve_pm_is_multiplier:
                config.points = config.points.model_copy(update={"ph_eve_pm_is_multiplier": val_eve_pm_is_mult})

        with eve3:
            st.markdown("##### 24H")
            val_eve_24h = st.number_input("Value (Eve 24H)", value=config.points.ph_eve_24h_multiplier)
            if val_eve_24h != config.points.ph_eve_24h_multiplier:
                config.points = config.points.model_copy(update={"ph_eve_24h_multiplier": val_eve_24h})

            val_eve_24h_is_mult = st.checkbox("Multiply? (Eve 24H)", value=config.points.ph_eve_24h_is_multiplier)
            if val_eve_24h_is_mult != config.points.ph_eve_24h_is_multiplier:
                config.points = config.points.model_copy(update={"ph_eve_24h_is_multiplier": val_eve_24h_is_mult})

        st.divider()

        # Row 3: Weekends
        st.markdown("**Weekends**")
        w1, w2 = st.columns(2)
        with w1:
            val_wknd = st.number_input("Weekend Value", value=config.points.weekend_multiplier)
            if val_wknd != config.points.weekend_multiplier:
                config.points = config.points.model_copy(update={"weekend_multiplier": val_wknd})
        with w2:
            val_wknd_is_mult = st.checkbox("Is Multiplier? (Wknd)", value=config.points.weekend_is_multiplier)
            if val_wknd_is_mult != config.points.weekend_is_multiplier:
                config.points = config.points.model_copy(update={"weekend_is_multiplier": val_wknd_is_mult})

        st.divider()

        # Row 4: Friday Shifts (Split)
        st.markdown("**Friday Shifts**")
        f1, f2, f3 = st.columns(3)

        # Column 1: AM
        with f1:
            st.markdown("##### AM")
            val_fri_am = st.number_input("Value (Fri AM)", value=config.points.friday_am_multiplier)
            if val_fri_am != config.points.friday_am_multiplier:
                config.points = config.points.model_copy(update={"friday_am_multiplier": val_fri_am})

            val_fri_am_is_mult = st.checkbox("Multiply? (Fri AM)", value=config.points.friday_am_is_multiplier)
            if val_fri_am_is_mult != config.points.friday_am_is_multiplier:
                config.points = config.points.model_copy(update={"friday_am_is_multiplier": val_fri_am_is_mult})

        # Column 2: PM
        with f2:
            st.markdown("##### PM")
            val_fri_pm = st.number_input("Value (Fri PM)", value=config.points.friday_pm_multiplier)
            if val_fri_pm != config.points.friday_pm_multiplier:
                config.points = config.points.model_copy(update={"friday_pm_multiplier": val_fri_pm})

            val_fri_pm_is_mult = st.checkbox("Multiply? (Fri PM)", value=config.points.friday_pm_is_multiplier)
            if val_fri_pm_is_mult != config.points.friday_pm_is_multiplier:
                config.points = config.points.model_copy(update={"friday_pm_is_multiplier": val_fri_pm_is_mult})

        # Column 3: 24H
        with f3:
            st.markdown("##### 24H")
            val_fri_24h = st.number_input("Value (Fri 24H)", value=config.points.friday_24h_multiplier)
            if val_fri_24h != config.points.friday_24h_multiplier:
                config.points = config.points.model_copy(update={"friday_24h_multiplier": val_fri_24h})

            val_fri_24h_is_mult = st.checkbox("Multiply? (Fri 24H)", value=config.points.friday_24h_is_multiplier)
            if val_fri_24h_is_mult != config.points.friday_24h_is_multiplier:
                config.points = config.points.model_copy(update={"friday_24h_is_multiplier": val_fri_24h_is_mult})

    st.info("Settings are applied in memory. Click 'Save Configuration' in the sidebar to persist to disk.")
