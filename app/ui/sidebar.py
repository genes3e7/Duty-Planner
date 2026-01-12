"""
app/ui/sidebar.py

Handles the sidebar navigation and configuration inputs.
"""

import datetime
import json
import logging

import pandas as pd
import streamlit as st

from app import logic
from app.core.data import DataManager
from app.models.config import AppConfig

logger = logging.getLogger(__name__)


def render_sidebar() -> str:
    """
    Renders the sidebar and returns the selected navigation page.
    """
    st.sidebar.title("Duty Planner")

    # 1. Navigation
    page = st.sidebar.radio("Navigation", ["Planner", "Settings"], key="navigation_radio")

    st.sidebar.divider()

    # 2. Configuration Loading
    st.sidebar.subheader("Configuration")

    # Check for existing config in session, else load template from server
    if "app_config" not in st.session_state:
        st.session_state.app_config = DataManager.load_config()

    config: AppConfig = st.session_state.app_config

    # Date Selection
    try:
        default_date = datetime.date(config.year, config.month, 1)
    except ValueError:
        default_date = datetime.date.today()

    col1, col2 = st.sidebar.columns(2)
    with col1:
        sel_year = st.number_input("Year", min_value=2000, max_value=2100, value=default_date.year, step=1)
    with col2:
        sel_month = st.number_input("Month", min_value=1, max_value=12, value=default_date.month, step=1)

    if sel_year != config.year or sel_month != config.month:
        config.year = int(sel_year)
        config.month = int(sel_month)
        # Invalidate planner cache if date changes
        st.session_state.loaded_date = None

    st.sidebar.divider()

    # --- Persistence: Client-Side Only ---
    st.sidebar.caption("💾 Save/Load Session")

    # A. Download (Save)
    st.sidebar.download_button(
        label="Download Config JSON",
        data=config.model_dump_json(indent=4),
        file_name=f"roster_config_{config.year}_{config.month}.json",
        mime="application/json",
        use_container_width=True,
    )

    # B. Upload (Load)
    uploaded_config = st.sidebar.file_uploader("Upload Config JSON", type=["json"], key="u_cfg")

    # Initialize state to track processed file and prevent infinite reruns
    if "config_upload_id" not in st.session_state:
        st.session_state.config_upload_id = None

    if uploaded_config is not None:
        # Identify the file uniquely (using name and size as proxy for ID)
        current_file_id = f"{uploaded_config.name}_{uploaded_config.size}"

        # Process only if this specific file hasn't been processed yet
        if st.session_state.config_upload_id != current_file_id:
            try:
                # Parse JSON dict
                content = uploaded_config.read()
                data = json.loads(content)
                
                # Robust validation: Fallback to current server config for any invalid fields
                new_config = AppConfig.from_dict_with_recovery(data, fallback=st.session_state.app_config)

                # Update session state
                st.session_state.app_config = new_config

                # Force reload of derived data if years/months changed or personnel changed
                st.session_state.loaded_date = None

                # Mark as processed so we don't re-enter this block after rerun
                st.session_state.config_upload_id = current_file_id

                st.toast("Configuration loaded successfully!", icon="✅")
                # Rerun to refresh the UI with new settings immediately
                st.rerun()

            except Exception as e:
                st.error(f"Invalid configuration file: {e}")
    else:
        # Reset tracker if file is removed so it can be re-uploaded if needed
        st.session_state.config_upload_id = None

    st.sidebar.divider()

    # 3. Import Features (Data)
    st.sidebar.subheader("Import Data")

    # --- A. Carry Forward & Init ---
    with st.sidebar.expander("1. Initialise / Carry Forward", expanded=False):
        st.caption("Upload previous month's roster to import 'Carry Over' points and initialize personnel.")
        uploaded_cf = st.file_uploader("Upload .xlsx", type=["xlsx"], key="u_cf")

        if uploaded_cf:
            if st.button("Confirm & Initialise", key="btn_cf"):
                try:
                    # 1. Load Balance
                    balance_data = DataManager.load_previous_balance(uploaded_cf)

                    if not balance_data:
                        st.error("No valid data found in file.")
                    else:
                        # 2. Update Session Balance
                        st.session_state.prev_balance = balance_data

                        # 3. Overwrite Personnel List
                        new_names = list(balance_data.keys())
                        if new_names:
                            config.personnel = new_names
                            st.success(f"Loaded {len(new_names)} staff & points.")

                            # 4. Force Roster Re-initialization
                            st.session_state.loaded_date = None
                        else:
                            st.warning("File loaded but contained no personnel data.")

                except (ValueError, pd.errors.EmptyDataError) as e:
                    st.error(f"Import failed: {e}")
                except Exception as e:
                    logger.exception("Unexpected error during carry-forward import")
                    st.error(f"Unexpected error: {e}")

    # --- B. Constraints Import ---
    with st.sidebar.expander("2. Import Constraints", expanded=False):
        st.caption("Batch upload constraints (e.g. 'X', 'AM') for the current roster.")
        uploaded_const = st.file_uploader("Upload .xlsx", type=["xlsx"], key="u_const")

        if uploaded_const:
            if st.button("Import Requests", key="btn_const"):
                # Check if roster exists to apply constraints to
                if "roster_df" not in st.session_state or st.session_state.roster_df is None:
                    # Try to initialize if we have date context
                    if st.session_state.loaded_date is None:
                        # Initialize silently if possible
                        r_df, d_df = logic.generate_empty_schedule(
                            config.year, config.month, config.personnel, config.country_code
                        )
                        st.session_state.roster_df = r_df
                        st.session_state.day_config_df = d_df
                        st.session_state.loaded_date = (config.year, config.month)

                try:
                    # Load and Apply
                    constraints = DataManager.load_constraints(uploaded_const)
                    if constraints:
                        updated_df = logic.apply_imported_constraints(st.session_state.roster_df, constraints)
                        st.session_state.roster_df = updated_df
                        st.session_state.roster_version = st.session_state.get("roster_version", 0) + 1
                        st.success("Constraints applied successfully!")
                    else:
                        st.warning("No constraints found or file empty.")
                except (ValueError, pd.errors.EmptyDataError) as e:
                    st.error(f"Constraint import failed: {e}")
                except Exception as e:
                    logger.exception("Unexpected error during constraint import")
                    st.error(f"Unexpected error: {e}")

    return page
