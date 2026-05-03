"""
app/ui/settings.py

Handles the configuration settings interface.
Allows modifying personnel list and point values.
"""

import holidays
import streamlit as st

from app.models.config import AppConfig


def _ensure_pending_state() -> None:
    """
    Initializes session state variables for tracking pending configuration changes.
    """
    if "pending_points_updates" not in st.session_state:
        st.session_state.pending_points_updates = {}
    if "pending_personnel_update" not in st.session_state:
        st.session_state.pending_personnel_update = None
    if "pending_country_code_update" not in st.session_state:
        st.session_state.pending_country_code_update = None


def _update_number_field(field_name: str, label: str, current_value: float) -> None:
    """Updates a numeric configuration field in the session state.

    Args:
        field_name: The internal name of the point setting.
        label: The display label for the input field.
        current_value: The current value of the field.
    """
    _ensure_pending_state()
    new_val = st.number_input(label, value=current_value, key=f"pt_{field_name}")
    if new_val != current_value:
        st.session_state.pending_points_updates[field_name] = new_val


def _update_checkbox_field(field_name: str, label: str, current_value: bool) -> None:
    """Updates a boolean configuration field in the session state.

    Args:
        field_name: The internal name of the toggle setting.
        label: The display label for the checkbox.
        current_value: The current value of the field.
    """
    _ensure_pending_state()
    new_val = st.checkbox(label, value=current_value, key=f"pt_bool_{field_name}")
    if new_val != current_value:
        st.session_state.pending_points_updates[field_name] = new_val


def render_settings(config: AppConfig) -> None:
    """
    Renders the settings page (Personnel & Points).
    """
    st.title("⚙️ Settings")

    _ensure_pending_state()

    # 1. Personnel Management
    st.subheader("Personnel")
    st.caption("Manage the list of staff available for duties.")

    current_names = ", ".join(config.personnel)
    new_names_str = st.text_area("Names (comma separated)", value=current_names, height=100)

    new_list = list(dict.fromkeys([n.strip() for n in new_names_str.split(",") if n.strip()]))

    if new_list != config.personnel:
        if not new_list:
            st.warning("Personnel list cannot be empty. At least one staff member is required.")
        else:
            st.session_state.pending_personnel_update = new_list

    st.markdown("---")

    # 2. General Settings (Country Code)
    st.subheader("General Settings")

    # Fetch supported countries
    try:
        supported_countries = sorted(holidays.list_supported_countries(include_aliases=False).keys())
    except Exception:
        supported_countries = ["SG", "US", "GB"]

    current_code = config.country_code
    index_val = supported_countries.index(current_code) if current_code in supported_countries else 0

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

    # 3. Point Values
    st.subheader("Point Scoring Rules")

    st.markdown("#### Base Points")
    p1, p2, p3, p4 = st.columns(4)

    # Standardized labels: "Shift Points"
    with p1:
        _update_number_field("AM", "AM Points", config.points.AM)
    with p2:
        _update_number_field("PM", "PM Points", config.points.PM)
    with p3:
        _update_number_field("FULL_24H", "24H Points", config.points.FULL_24H)
    with p4:
        _update_number_field("SB", "Standby Points", config.points.SB)

    st.divider()

    st.markdown("#### Multipliers")
    st.caption(
        "Define bonus logic. If 'Is Multiplier?' is checked, points are multiplied (e.g. 2x). "
        "Otherwise, value is added (e.g. +2)."
    )

    # 1. Weekends
    st.markdown("**Weekends**")
    w1, w2 = st.columns(2)
    with w1:
        _update_number_field("weekend_multiplier", "Value", config.points.weekend_multiplier)
    with w2:
        _update_checkbox_field("weekend_is_multiplier", "Is Multiplier?", config.points.weekend_is_multiplier)

    st.divider()

    # 2. Friday Shifts
    st.markdown("**Friday Shifts**")
    f1, f2, f3 = st.columns(3)
    # Standardized labels: "Value" and "Is Multiplier?"
    with f1:
        st.markdown("##### AM")
        _update_number_field("friday_am_multiplier", "Value", config.points.friday_am_multiplier)
        _update_checkbox_field("friday_am_is_multiplier", "Is Multiplier?", config.points.friday_am_is_multiplier)
    with f2:
        st.markdown("##### PM")
        _update_number_field("friday_pm_multiplier", "Value", config.points.friday_pm_multiplier)
        _update_checkbox_field("friday_pm_is_multiplier", "Is Multiplier?", config.points.friday_pm_is_multiplier)
    with f3:
        st.markdown("##### 24H")
        _update_number_field("friday_24h_multiplier", "Value", config.points.friday_24h_multiplier)
        _update_checkbox_field("friday_24h_is_multiplier", "Is Multiplier?", config.points.friday_24h_is_multiplier)

    st.divider()

    # 3. Public Holidays
    st.markdown("**Public Holidays**")
    ph1, ph2 = st.columns(2)
    with ph1:
        _update_number_field("ph_multiplier", "Value", config.points.ph_multiplier)
    with ph2:
        _update_checkbox_field("ph_is_multiplier", "Is Multiplier?", config.points.ph_is_multiplier)

    st.divider()

    # 4. Public Holiday Eves
    st.markdown("**Public Holiday Eves**")
    eve1, eve2, eve3 = st.columns(3)
    with eve1:
        st.markdown("##### AM")
        _update_number_field("ph_eve_am_multiplier", "Value", config.points.ph_eve_am_multiplier)
        _update_checkbox_field("ph_eve_am_is_multiplier", "Is Multiplier?", config.points.ph_eve_am_is_multiplier)
    with eve2:
        st.markdown("##### PM")
        _update_number_field("ph_eve_pm_multiplier", "Value", config.points.ph_eve_pm_multiplier)
        _update_checkbox_field("ph_eve_pm_is_multiplier", "Is Multiplier?", config.points.ph_eve_pm_is_multiplier)
    with eve3:
        st.markdown("##### 24H")
        _update_number_field("ph_eve_24h_multiplier", "Value", config.points.ph_eve_24h_multiplier)
        _update_checkbox_field("ph_eve_24h_is_multiplier", "Is Multiplier?", config.points.ph_eve_24h_is_multiplier)

    # Apply pending updates
    if "pending_points_updates" in st.session_state and st.session_state.pending_points_updates:
        config.points = config.points.model_copy(update=st.session_state.pending_points_updates)
        st.session_state.pending_points_updates = {}

    if st.session_state.get("pending_personnel_update") is not None:
        config.personnel = st.session_state.pending_personnel_update
        st.session_state.pending_personnel_update = None

    if st.session_state.get("pending_country_code_update") is not None:
        config.country_code = st.session_state.pending_country_code_update
        st.session_state.pending_country_code_update = None
        if "loaded_date" in st.session_state:
            st.session_state.loaded_date = None

    st.info(
        "Settings are applied in memory. To save these changes permanently, "
        "go to the sidebar and click **Download Config JSON**."
    )
