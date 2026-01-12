"""
app/ui/settings.py

Handles the configuration settings interface.
Allows modifying personnel list, shift constraints, and point values.
"""

import streamlit as st

from app.models.config import AppConfig


def _update_number_field(config: AppConfig, field_name: str, label: str, current_value: float) -> None:
    """Helper to update a numeric point field with validation."""
    new_val = st.number_input(label, value=current_value)
    if new_val != current_value:
        config.points = config.points.model_copy(update={field_name: new_val})


def _update_checkbox_field(config: AppConfig, field_name: str, label: str, current_value: bool) -> None:
    """Helper to update a boolean point field with validation."""
    new_val = st.checkbox(label, value=current_value)
    if new_val != current_value:
        config.points = config.points.model_copy(update={field_name: new_val})


def render_settings(config: AppConfig) -> None:
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
            # Removed redundant int() cast; st.number_input with format="%d" handles display,
            # and we can cast the result if needed or rely on step=1.
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

        with p1:
            _update_number_field(config, "AM", "AM Pts", config.points.AM)
        with p2:
            _update_number_field(config, "PM", "PM Pts", config.points.PM)
        with p3:
            _update_number_field(config, "FULL_24H", "24H Pts", config.points.FULL_24H)
        with p4:
            _update_number_field(config, "SB", "Standby Pts", config.points.SB)

    with st.expander("Multipliers", expanded=True):
        st.caption("Multipliers scale the base points (e.g. 2x). If unchecked, the value is added (e.g. +2).")

        # Row 1: Public Holidays & Eves
        st.markdown("**Public Holidays**")
        ph1, ph2 = st.columns(2)
        with ph1:
            _update_number_field(config, "ph_multiplier", "PH Value", config.points.ph_multiplier)
        with ph2:
            _update_checkbox_field(config, "ph_is_multiplier", "Is Multiplier? (PH)", config.points.ph_is_multiplier)

        st.divider()

        # Row 2: Public Holiday Eves (Split)
        st.markdown("**Public Holiday Eves**")
        eve1, eve2, eve3 = st.columns(3)

        with eve1:
            st.markdown("##### AM")
            _update_number_field(config, "ph_eve_am_multiplier", "Value (Eve AM)", config.points.ph_eve_am_multiplier)
            _update_checkbox_field(
                config, "ph_eve_am_is_multiplier", "Multiply? (Eve AM)", config.points.ph_eve_am_is_multiplier
            )

        with eve2:
            st.markdown("##### PM")
            _update_number_field(config, "ph_eve_pm_multiplier", "Value (Eve PM)", config.points.ph_eve_pm_multiplier)
            _update_checkbox_field(
                config, "ph_eve_pm_is_multiplier", "Multiply? (Eve PM)", config.points.ph_eve_pm_is_multiplier
            )

        with eve3:
            st.markdown("##### 24H")
            _update_number_field(
                config, "ph_eve_24h_multiplier", "Value (Eve 24H)", config.points.ph_eve_24h_multiplier
            )
            _update_checkbox_field(
                config, "ph_eve_24h_is_multiplier", "Multiply? (Eve 24H)", config.points.ph_eve_24h_is_multiplier
            )

        st.divider()

        # Row 3: Weekends
        st.markdown("**Weekends**")
        w1, w2 = st.columns(2)
        with w1:
            _update_number_field(config, "weekend_multiplier", "Weekend Value", config.points.weekend_multiplier)
        with w2:
            _update_checkbox_field(
                config, "weekend_is_multiplier", "Is Multiplier? (Wknd)", config.points.weekend_is_multiplier
            )

        st.divider()

        # Row 4: Friday Shifts (Split)
        st.markdown("**Friday Shifts**")
        f1, f2, f3 = st.columns(3)

        # Column 1: AM
        with f1:
            st.markdown("##### AM")
            _update_number_field(config, "friday_am_multiplier", "Value (Fri AM)", config.points.friday_am_multiplier)
            _update_checkbox_field(
                config, "friday_am_is_multiplier", "Multiply? (Fri AM)", config.points.friday_am_is_multiplier
            )

        # Column 2: PM
        with f2:
            st.markdown("##### PM")
            _update_number_field(config, "friday_pm_multiplier", "Value (Fri PM)", config.points.friday_pm_multiplier)
            _update_checkbox_field(
                config, "friday_pm_is_multiplier", "Multiply? (Fri PM)", config.points.friday_pm_is_multiplier
            )

        # Column 3: 24H
        with f3:
            st.markdown("##### 24H")
            _update_number_field(
                config, "friday_24h_multiplier", "Value (Fri 24H)", config.points.friday_24h_multiplier
            )
            _update_checkbox_field(
                config, "friday_24h_is_multiplier", "Multiply? (Fri 24H)", config.points.friday_24h_is_multiplier
            )

    st.info("Settings are applied in memory. Click 'Save Configuration' in the sidebar to persist to disk.")
