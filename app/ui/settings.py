"""
app/ui/settings.py

Handles the configuration settings interface.
Allows modifying personnel list, shift constraints, and point values.
"""

import holidays
import streamlit as st

from app.models.config import AppConfig


def _ensure_pending_state() -> None:
    if "pending_points_updates" not in st.session_state:
        st.session_state.pending_points_updates = {}
    if "pending_constraints_updates" not in st.session_state:
        st.session_state.pending_constraints_updates = {}
    if "pending_personnel_update" not in st.session_state:
        st.session_state.pending_personnel_update = None
    if "pending_standby_update" not in st.session_state:
        st.session_state.pending_standby_update = None
    if "pending_max_consecutive_update" not in st.session_state:
        st.session_state.pending_max_consecutive_update = None
    if "pending_country_code_update" not in st.session_state:
        st.session_state.pending_country_code_update = None
    if "pending_timeout_update" not in st.session_state:
        st.session_state.pending_timeout_update = None


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

    # 2. General Settings (Country Code)
    st.subheader("General Settings")
    st.caption("Settings that affect holidays and global behavior.")

    # Fetch supported countries from the holidays library
    try:
        supported_countries = sorted(holidays.list_supported_countries(include_aliases=False).keys())
    except Exception:
        supported_countries = ["SG", "US", "GB"]  # Fallback

    # Determine current index
    current_code = config.country_code
    if current_code in supported_countries:
        index_val = supported_countries.index(current_code)
    else:
        # Default to SG if current is invalid, or 0 if SG not found
        index_val = supported_countries.index("SG") if "SG" in supported_countries else 0

    country_val = st.selectbox(
        "Country Code (for Public Holidays)",
        options=supported_countries,
        index=index_val,
        help="Select the country for public holiday calculations.",
        key="country_code_select",
    )

    if country_val != config.country_code:
        st.session_state.pending_country_code_update = country_val

    st.markdown("---")

    # 3. Shift Constraints
    st.subheader("Shift Constraints")

    c1, c2, c3, c4 = st.columns(4)
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

    with c4:
        val_sb = int(
            st.number_input(
                "S/B Staff Needed",
                min_value=0,
                value=config.constraints.standby_per_day,
                step=1,
                format="%d",
                key="constraint_sb",
            )
        )
        if val_sb != config.constraints.standby_per_day:
            st.session_state.pending_standby_update = val_sb

    # Max Consecutive Duties & Timeout
    st.caption("Global limits applied to all staff.")

    col_max, col_timeout = st.columns(2)

    with col_max:
        val_max = int(
            st.number_input(
                "Max Consecutive Duties",
                min_value=1,
                value=config.constraints.max_consecutive_duties,
                step=1,
                format="%d",
                key="constraint_max_consecutive",
            )
        )
        if val_max != config.constraints.max_consecutive_duties:
            st.session_state.pending_max_consecutive_update = val_max

    with col_timeout:
        val_timeout = float(
            st.number_input(
                "Solver Timeout (seconds)",
                min_value=1.0,
                value=float(config.constraints.solver_timeout_seconds),
                step=5.0,
                format="%.1f",
                key="constraint_timeout",
            )
        )
        if val_timeout != config.constraints.solver_timeout_seconds:
            st.session_state.pending_timeout_update = val_timeout

    st.markdown("---")

    # 4. Point Values
    st.subheader("Point Scoring Rules")

    st.markdown("#### Base Points")
    p1, p2, p3, p4 = st.columns(4)

    with p1:
        _update_number_field("AM", "AM Pts", config.points.AM)
    with p2:
        _update_number_field("PM", "PM Pts", config.points.PM)
    with p3:
        _update_number_field("FULL_24H", "24H Pts", config.points.FULL_24H)
    with p4:
        _update_number_field("SB", "Standby Pts", config.points.SB)

    st.divider()

    st.markdown("#### Multipliers")
    st.caption("Multipliers scale the base points (e.g. 2x). If unchecked, the value is added (e.g. +2).")

    # 1. Weekends
    st.markdown("**Weekends**")
    w1, w2 = st.columns(2)
    with w1:
        _update_number_field("weekend_multiplier", "Weekend Value", config.points.weekend_multiplier)
    with w2:
        _update_checkbox_field("weekend_is_multiplier", "Is Multiplier? (Wknd)", config.points.weekend_is_multiplier)

    st.divider()

    # 2. Friday Shifts (Split)
    st.markdown("**Friday Shifts**")
    f1, f2, f3 = st.columns(3)

    # Column 1: AM
    with f1:
        st.markdown("##### AM")
        _update_number_field("friday_am_multiplier", "Value (Fri AM)", config.points.friday_am_multiplier)
        _update_checkbox_field("friday_am_is_multiplier", "Multiply? (Fri AM)", config.points.friday_am_is_multiplier)

    # Column 2: PM
    with f2:
        st.markdown("##### PM")
        _update_number_field("friday_pm_multiplier", "Value (Fri PM)", config.points.friday_pm_multiplier)
        _update_checkbox_field("friday_pm_is_multiplier", "Multiply? (Fri PM)", config.points.friday_pm_is_multiplier)

    # Column 3: 24H
    with f3:
        st.markdown("##### 24H")
        _update_number_field("friday_24h_multiplier", "Value (Fri 24H)", config.points.friday_24h_multiplier)
        _update_checkbox_field(
            "friday_24h_is_multiplier", "Multiply? (Fri 24H)", config.points.friday_24h_is_multiplier
        )

    st.divider()

    # 3. Public Holidays
    st.markdown("**Public Holidays**")
    ph1, ph2 = st.columns(2)
    with ph1:
        _update_number_field("ph_multiplier", "PH Value", config.points.ph_multiplier)
    with ph2:
        _update_checkbox_field("ph_is_multiplier", "Is Multiplier? (PH)", config.points.ph_is_multiplier)

    st.divider()

    # 4. Public Holiday Eves (Split)
    st.markdown("**Public Holiday Eves**")
    eve1, eve2, eve3 = st.columns(3)

    with eve1:
        st.markdown("##### AM")
        _update_number_field("ph_eve_am_multiplier", "Value (Eve AM)", config.points.ph_eve_am_multiplier)
        _update_checkbox_field("ph_eve_am_is_multiplier", "Multiply? (Eve AM)", config.points.ph_eve_am_is_multiplier)

    with eve2:
        st.markdown("##### PM")
        _update_number_field("ph_eve_pm_multiplier", "Value (Eve PM)", config.points.ph_eve_pm_multiplier)
        _update_checkbox_field("ph_eve_pm_is_multiplier", "Multiply? (Eve PM)", config.points.ph_eve_pm_is_multiplier)

    with eve3:
        st.markdown("##### 24H")
        _update_number_field("ph_eve_24h_multiplier", "Value (Eve 24H)", config.points.ph_eve_24h_multiplier)
        _update_checkbox_field(
            "ph_eve_24h_is_multiplier", "Multiply? (Eve 24H)", config.points.ph_eve_24h_is_multiplier
        )

    # Apply pending updates if any exist
    if "pending_points_updates" in st.session_state and st.session_state.pending_points_updates:
        config.points = config.points.model_copy(update=st.session_state.pending_points_updates)
        st.session_state.pending_points_updates = {}

    constraint_updates = {}
    if "pending_constraints_updates" in st.session_state and st.session_state.pending_constraints_updates:
        new_constraints = {
            **config.constraints.personnel_needed_per_shift,
            **st.session_state.pending_constraints_updates,
        }
        constraint_updates["personnel_needed_per_shift"] = new_constraints
        st.session_state.pending_constraints_updates = {}

    if st.session_state.get("pending_standby_update") is not None:
        constraint_updates["standby_per_day"] = st.session_state.pending_standby_update
        st.session_state.pending_standby_update = None

    if st.session_state.get("pending_max_consecutive_update") is not None:
        constraint_updates["max_consecutive_duties"] = st.session_state.pending_max_consecutive_update
        st.session_state.pending_max_consecutive_update = None

    if st.session_state.get("pending_timeout_update") is not None:
        constraint_updates["solver_timeout_seconds"] = st.session_state.pending_timeout_update
        st.session_state.pending_timeout_update = None

    if constraint_updates:
        config.constraints = config.constraints.model_copy(update=constraint_updates)

    if st.session_state.get("pending_personnel_update") is not None:
        config.personnel = st.session_state.pending_personnel_update
        st.session_state.pending_personnel_update = None

    if st.session_state.get("pending_country_code_update") is not None:
        config.country_code = st.session_state.pending_country_code_update
        st.session_state.pending_country_code_update = None
        # Invalidate planner cache to force reload with new holidays
        if "loaded_date" in st.session_state:
            st.session_state.loaded_date = None

    st.info(
        "Settings are applied in memory. To save these changes permanently, "
        "go to the sidebar and click **Download Config JSON**."
    )
