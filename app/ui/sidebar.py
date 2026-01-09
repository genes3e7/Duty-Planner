import calendar
import datetime
import os
import tempfile

import streamlit as st

from app import logic
from app.core.data import DataManager


def render_sidebar():
    """Renders the sidebar and returns the selected (year, month, month_name)."""
    with st.sidebar:
        st.title("Duty Planner")

        # Date Picker
        # Logic: Default to NEXT month (as planning is usually future-facing)
        today = datetime.date.today()
        if today.month == 12:
            next_month_val = datetime.date(today.year + 1, 1, 1)
        else:
            next_month_val = datetime.date(today.year, today.month + 1, 1)

        default_date = next_month_val

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
        if st.button("🔄 Load / Reset Grid", type="primary", width="stretch"):
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
                # Use tempfile to prevent race conditions and conflicts
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                    tmp.write(up_file.getbuffer())
                    temp_path = tmp.name

                try:
                    prev = DataManager.load_previous_balance(temp_path)
                    st.session_state.prev_balance = prev
                    st.success(f"Imported {len(prev)} balance records!")

                    if st.button("Update Personnel List?"):
                        st.session_state.config.personnel = sorted(list(prev.keys()))
                        st.success("Personnel list updated!")
                        st.rerun()

                except Exception as e:
                    st.error(f"Error: {e}")
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

    return sel_year, sel_month, sel_month_name
