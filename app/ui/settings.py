"""
app/ui/settings.py

Handles the configuration settings interface.
Allows modifying personnel list, shift constraints, and point values.
"""

import streamlit as st

from app.models.config import AppConfig


def _ensure_pending_state() -> None:
    if "pending_points_updates" not in st.session_state:
        st.session_state.pending_points_updates = {}
    if "pending_constraints_updates" not in st.session_state:
        st.session_state.pending_constraints_updates = {}
    if "pending_personnel_update" not in st.session_state:
        st.session_state.pending_personnel_update = None


def _update_number_field(field_name: str, label: str, current_value: float) -> None:
    """Helper to track a numeric point field change in session state."""
    _ensure_pending_state()
    # Use key to let Streamlit manage the widget state uniquely
    new_val = st.number_input(label, value=current_value, key=f"pt_{field_name}")
    if new_val != current_value:
        st.session_state.pending_points_updates[field_name] = new_val


def _update_checkbox_field(field_name: str, label: str, current_value: bool) -> None:
    """Helper to track a boolean point field change in session state."""
    _ensure_pending_state()
    new_val = st.checkbox(label, value=current_value, key=f"pt_bool_{field_name}")
    if new_val != current_value:
        st.session_state.pending_points_updates[field_name] = new_val


def render_settings(config: AppConfig) -> None:
    """
    Renders the settings page.

    Args:
        config (AppConfig): The application configuration object to edit.
    """
    st.title("⚙️ Settings")

    # Ensure pending states are initialized at the start
    _ensure_pending_state()

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
            # Set pending update instead of direct mutation
            st.session_state.pending_personnel_update = new_list
        # We don't rerun here to allow bulk edits, but data binds to the object reference

    st.markdown("---")

    # 2. Shift Constraints
    st.subheader("Shift Constraints")

    c1, c2, c3 = st.columns(3)
    shifts = [("AM", c1), ("PM", c2), ("24H", c3)]

    for shift_name, col in shifts:
        with col:
            # Cast to int since st.number_input returns float by default
            val = int(
                st.number_input(
                    f"{shift_name} Staff Needed",
                    min_value=0,
                    value=config.constraints.personnel_needed_per_shift.get(shift_name, 1),
                    step=1,
                    format="%d",
                    key=f"constraint_{shift_name}",
                )
            )
            # Use same default as value retrieval to avoid comparing int to None
            if val != config.constraints.personnel_needed_per_shift.get(shift_name, 1):
                st.session_state.pending_constraints_updates[shift_name] = val

    st.markdown("---")

    # 3. Point Values
    st.subheader("Point Scoring Rules")

    with st.expander("Base Points"):
        p1, p2, p3, p4 = st.columns(4)

        with p1:
            _update_number_field("AM", "AM Pts", config.points.AM)
        with p2:
            _update_number_field("PM", "PM Pts", config.points.PM)
        with p3:
            _update_number_field("FULL_24H", "24H Pts", config.points.FULL_24H)
        with p4:
            _update_number_field("SB", "Standby Pts", config.points.SB)

    with st.expander("Multipliers", expanded=True):
        st.caption("Multipliers scale the base points (e.g. 2x). If unchecked, the value is added (e.g. +2).")

        # Row 1: Public Holidays & Eves
        st.markdown("**Public Holidays**")
        ph1, ph2 = st.columns(2)
        with ph1:
            _update_number_field("ph_multiplier", "PH Value", config.points.ph_multiplier)
        with ph2:
            _update_checkbox_field("ph_is_multiplier", "Is Multiplier? (PH)", config.points.ph_is_multiplier)

        st.divider()

        # Row 2: Public Holiday Eves (Split)
        st.markdown("**Public Holiday Eves**")
        eve1, eve2, eve3 = st.columns(3)

        with eve1:
            st.markdown("##### AM")
            _update_number_field("ph_eve_am_multiplier", "Value (Eve AM)", config.points.ph_eve_am_multiplier)
            _update_checkbox_field(
                "ph_eve_am_is_multiplier", "Multiply? (Eve AM)", config.points.ph_eve_am_is_multiplier
            )

        with eve2:
            st.markdown("##### PM")
            _update_number_field("ph_eve_pm_multiplier", "Value (Eve PM)", config.points.ph_eve_pm_multiplier)
            _update_checkbox_field(
                "ph_eve_pm_is_multiplier", "Multiply? (Eve PM)", config.points.ph_eve_pm_is_multiplier
            )

        with eve3:
            st.markdown("##### 24H")
            _update_number_field("ph_eve_24h_multiplier", "Value (Eve 24H)", config.points.ph_eve_24h_multiplier)
            _update_checkbox_field(
                "ph_eve_24h_is_multiplier", "Multiply? (Eve 24H)", config.points.ph_eve_24h_is_multiplier
            )

        st.divider()

        # Row 3: Weekends
        st.markdown("**Weekends**")
        w1, w2 = st.columns(2)
        with w1:
            _update_number_field("weekend_multiplier", "Weekend Value", config.points.weekend_multiplier)
        with w2:
            _update_checkbox_field(
                "weekend_is_multiplier", "Is Multiplier? (Wknd)", config.points.weekend_is_multiplier
            )

        st.divider()

        # Row 4: Friday Shifts (Split)
        st.markdown("**Friday Shifts**")
        f1, f2, f3 = st.columns(3)

        # Column 1: AM
        with f1:
            st.markdown("##### AM")
            _update_number_field("friday_am_multiplier", "Value (Fri AM)", config.points.friday_am_multiplier)
            _update_checkbox_field(
                "friday_am_is_multiplier", "Multiply? (Fri AM)", config.points.friday_am_is_multiplier
            )

        # Column 2: PM
        with f2:
            st.markdown("##### PM")
            _update_number_field("friday_pm_multiplier", "Value (Fri PM)", config.points.friday_pm_multiplier)
            _update_checkbox_field(
                "friday_pm_is_multiplier", "Multiply? (Fri PM)", config.points.friday_pm_is_multiplier
            )

        # Column 3: 24H
        with f3:
            st.markdown("##### 24H")
            _update_number_field("friday_24h_multiplier", "Value (Fri 24H)", config.points.friday_24h_multiplier)
            _update_checkbox_field(
                "friday_24h_is_multiplier", "Multiply? (Fri 24H)", config.points.friday_24h_is_multiplier
            )

    # Apply pending updates if any exist
    if "pending_points_updates" in st.session_state and st.session_state.pending_points_updates:
        config.points = config.points.model_copy(update=st.session_state.pending_points_updates)
        st.session_state.pending_points_updates = {}

    if "pending_constraints_updates" in st.session_state and st.session_state.pending_constraints_updates:
        new_constraints = {
            **config.constraints.personnel_needed_per_shift,
            **st.session_state.pending_constraints_updates,
        }
        # Use model_copy for consistency with the immutable pattern used for points
        config.constraints = config.constraints.model_copy(update={"personnel_needed_per_shift": new_constraints})
        st.session_state.pending_constraints_updates = {}

    if st.session_state.get("pending_personnel_update") is not None:
        config.personnel = st.session_state.pending_personnel_update
        st.session_state.pending_personnel_update = None

    st.info(
        "Settings are applied in memory. To save these changes permanently, "
        "go to the sidebar and click **Download Config JSON**."
    )
