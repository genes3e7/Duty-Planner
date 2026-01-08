import calendar
import datetime
import os

import streamlit as st

from app import logic
from app.core.data import DataManager


def render_sidebar():
    """Renders the sidebar and returns the selected (year, month, month_name)."""
    with st.sidebar:
        st.title("Duty Planner")

        # Date Picker
        try:
            # Safely get default date
            default_date = datetime.date(st.session_state.config.year, st.session_state.config.month, 1)
        except (ValueError, AttributeError):
            default_date = datetime.date.today().replace(day=1)

        sel_date = st.date_input(
            "Select Planning Month",
            value=default_date,
            min_value=datetime.date(2000, 1, 1),
            help="Pick any day in the month you want to plan for.",
        )

        sel_year = sel_date.year
        sel_month = sel_date.month
        sel_month_name = calendar.month_name[sel_month]

        st.caption(f"Selected: **{sel_month_name} {sel_year}**")

        st.divider()

        # Load Grid
        if st.button("🔄 Load / Reset Grid", type="primary", use_container_width=True):
            r_df, d_df = logic.generate_empty_schedule(sel_year, sel_month, st.session_state.config.personnel)
            st.session_state.roster_df = r_df
            st.session_state.day_config_df = d_df
            st.session_state.config.year = sel_year
            st.session_state.config.month = sel_month
            st.session_state.loaded_date = (sel_year, sel_month)
            st.rerun()

        st.divider()

        # Import Balance
        with st.expander("📥 Import Balance"):
            st.caption("Upload previous month's Excel export to carry over points.")
            up_file = st.file_uploader("Upload .xlsx", type=["xlsx"])
            if up_file:
                temp_path = "temp_import.xlsx"
                try:
                    with open(temp_path, "wb") as f:
                        f.write(up_file.getbuffer())

                    prev = DataManager.load_previous_balance(temp_path)
                    st.session_state.prev_balance = prev

                    if st.button("Update Personnel List?"):
                        st.session_state.config.personnel = sorted(list(prev.keys()))
                        st.rerun()

                    st.success(f"Imported {len(prev)} records!")
                except Exception as e:
                    st.error(f"Error: {e}")
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

    return sel_year, sel_month, sel_month_name
