"""
app/ui/planner.py

Handles the main planning interface:
- Roster Grid (Editable)
- Day Configuration
- Solver Trigger
- Statistics Display
"""

import calendar
import logging

import pandas as pd
import streamlit as st

from app import logic
from app.models.config import AppConfig

# --- FIXED IMPORT ---
from app.utils.helpers import get_shift_name

logger = logging.getLogger(__name__)


def _initialize_session_state(config: AppConfig, sel_year: int, sel_month: int, sel_month_name: str) -> None:
    """Initializes or updates the session state for the selected date."""
    current_date_key = (sel_year, sel_month)

    if "loaded_date" not in st.session_state:
        st.session_state.loaded_date = None

    data_needs_init = st.session_state.get("roster_df") is None
    date_changed = st.session_state.loaded_date != current_date_key

    if data_needs_init or date_changed:
        if date_changed and st.session_state.loaded_date is not None:
            st.toast(f"Switched to {sel_month_name} {sel_year}", icon="📅")

        # Pass country_code to generate appropriate holidays
        r_df, d_df = logic.generate_empty_schedule(sel_year, sel_month, config.personnel, config.country_code)

        st.session_state.roster_df = r_df
        st.session_state.day_config_df = d_df
        st.session_state.loaded_date = current_date_key
        st.session_state.roster_version = 0

    if "prev_balance" not in st.session_state:
        st.session_state.prev_balance = {}

    # Update Index Name to show Month/Year in top-left
    if st.session_state.roster_df is not None:
        st.session_state.roster_df.index.name = f"{sel_month_name} {sel_year}"


def _render_toolbar(config: AppConfig, sel_year: int, sel_month: int) -> None:
    """Renders the action buttons (Reset, Clear, Solver)."""
    col_act1, col_act2, col_act3 = st.columns([1, 1, 2])

    with col_act1:
        if st.button("🔄 Reset Grid", help="Clear all data for this month"):
            r_df, d_df = logic.generate_empty_schedule(sel_year, sel_month, config.personnel, config.country_code)
            st.session_state.roster_df = r_df
            st.session_state.day_config_df = d_df
            st.session_state.roster_version += 1
            st.rerun()

    with col_act2:
        if st.button("🧹 Clear Duties", help="Keep 'X', clear others"):
            st.session_state.roster_df = logic.clear_schedule(st.session_state.roster_df, clear_constraints=False)
            st.session_state.roster_version += 1
            st.rerun()

    with col_act3:
        if st.button("🚀 Auto-Fill Schedule", type="primary", use_container_width=True):
            with st.spinner("Solving..."):
                res = logic.run_solver(
                    sel_year,
                    sel_month,
                    st.session_state.roster_df,
                    st.session_state.day_config_df,
                    config,
                    st.session_state.prev_balance,
                )
                if res:
                    sched, _ = res
                    for (p, d), s in sched.items():
                        col_name = f"D{d}"
                        if p in st.session_state.roster_df.index and col_name in st.session_state.roster_df.columns:
                            st.session_state.roster_df.at[p, col_name] = s
                    st.success("Optimization Complete!")
                    st.session_state.roster_version += 1
                    st.rerun()
                else:
                    st.error("No solution found. Check constraints.")


def _render_day_config() -> None:
    """Renders the expandable Day Settings configuration."""
    with st.expander("⚙️ Day Settings & Constraints", expanded=False):
        st.caption("Configure which days are Holidays (24H) or active.")

        # Bulk Action Buttons
        b_col1, b_col2 = st.columns(2)
        with b_col1:
            if st.button("Set All to Shift (AM/PM)", use_container_width=True):
                st.session_state.day_config_df["Mode"] = "SHIFT"
                st.rerun()
        with b_col2:
            if st.button("Set All to 24H", use_container_width=True):
                st.session_state.day_config_df["Mode"] = "24H"
                st.rerun()

        edited_day_config = st.data_editor(
            st.session_state.day_config_df,
            column_config={
                "Active": st.column_config.CheckboxColumn("Active?", width="small"),
                "Mode": st.column_config.SelectboxColumn(
                    "Mode", options=["SHIFT", "24H"], width="medium", required=True
                ),
                "Is_PH": st.column_config.CheckboxColumn("PH", width="small"),
            },
            # Hiding "Is_Weekend" by strictly defining column_order
            column_order=["Active", "Mode", "Is_PH"],
            disabled=["Date"],
            width="stretch",
            key="day_config_editor",
        )
        if not edited_day_config.equals(st.session_state.day_config_df):
            st.session_state.day_config_df = edited_day_config
            st.rerun()


def _render_roster_grid(sel_year: int, sel_month: int) -> None:
    """Renders the main editable roster grid."""
    st.subheader("Assignments")

    column_config = {}

    # Retrieve team counts from current config
    num_active = st.session_state.app_config.constraints.num_active_teams
    num_sb = st.session_state.app_config.constraints.num_standby_teams

    for col_name in st.session_state.roster_df.columns:
        day_num = logic.get_day_num(col_name)
        if day_num > 0 and day_num in st.session_state.day_config_df.index:
            row_config = st.session_state.day_config_df.loc[day_num]
            mode = row_config["Mode"]
            is_active = row_config["Active"]
            is_ph = row_config["Is_PH"]

            # Construct Header Label: e.g. "1 Mon" or "1 Mon 🏖️"
            try:
                date_obj = pd.Timestamp(year=sel_year, month=sel_month, day=day_num)
                day_str = date_obj.strftime("%a")  # Mon, Tue
                label = f"{day_num} {day_str}"
            except (ValueError, OverflowError):
                label = str(day_num)

            # Visual Indicators in Header
            if is_ph:
                label += " 🏖️"

            if not is_active:
                label += " 🚫"

            # Construct Options dynamically
            opts = ["", "X"]

            # Add Active Teams
            for t in range(1, num_active + 1):
                if mode == "24H":
                    opts.append(get_shift_name("24H", t))
                else:
                    opts.append(get_shift_name("AM", t))
                    opts.append(get_shift_name("PM", t))

            # Add Standby Teams
            for t in range(1, num_sb + 1):
                opts.append(get_shift_name("S/B", t))

            column_config[col_name] = st.column_config.SelectboxColumn(
                label=label,
                options=opts,
                width=90,  # Custom pixel width: tight fit for Emoji
                required=False,
                disabled=not is_active,  # Disable the column if day is inactive
            )

    edited_roster = st.data_editor(
        st.session_state.roster_df,
        column_config=column_config,
        width="stretch",
        height=500,
        key=f"roster_editor_{st.session_state.roster_version}",
    )

    if not edited_roster.equals(st.session_state.roster_df):
        st.session_state.roster_df = edited_roster
        st.rerun()


def _render_statistics(config: AppConfig, sel_year: int, sel_month: int) -> None:
    """Calculates and renders statistics and export options."""
    st.divider()
    st.subheader("Statistics")

    stats_df = logic.calculate_stats(
        st.session_state.roster_df, st.session_state.day_config_df, config, st.session_state.prev_balance
    )

    if stats_df.empty or "Month Pts" not in stats_df.columns:
        total_month = 0.0
        avg_month = 0.0
        std_total = 0.0
    else:
        total_month = stats_df["Month Pts"].sum()
        avg_month = stats_df["Month Pts"].mean()

        # Fairness Metric: Standard Deviation should be based on CUMULATIVE points (Carry Over)
        # to ensure long-term balance, not just monthly balance.
        if "Carry Over" in stats_df.columns:
            std_total = stats_df["Carry Over"].std()
        else:
            std_total = 0.0

        if pd.isna(std_total):
            std_total = 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("Month Pts", f"{total_month:.1f}")
    c2.metric("Avg Pts", f"{avg_month:.2f}")
    c3.metric("Std Dev (Total)", f"{std_total:.2f}", help="Standard Deviation of cumulative Carry Over points.")

    st.dataframe(stats_df, width="stretch", hide_index=True)

    xlsx_data = logic.export_to_excel_bytes(st.session_state.roster_df, stats_df, config)
    st.download_button(
        "📥 Download Roster (.xlsx)",
        data=xlsx_data,
        file_name=f"Roster_{sel_year}_{sel_month}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


def render_planner(config: AppConfig) -> None:
    """
    Renders the main planning grid and actions.

    Args:
        config (AppConfig): The application configuration containing
                            current year, month, and personnel.
    """
    sel_year = config.year
    sel_month = config.month
    sel_month_name = calendar.month_name[sel_month]

    st.title(f"🗓️ Roster: {sel_month_name} {sel_year}")

    # 1. Initialize Session
    _initialize_session_state(config, sel_year, sel_month, sel_month_name)

    # 2. Render Toolbar
    _render_toolbar(config, sel_year, sel_month)

    # 3. Render Day Config
    _render_day_config()

    # 4. Render Roster Grid
    _render_roster_grid(sel_year, sel_month)

    # 5. Render Statistics
    _render_statistics(config, sel_year, sel_month)
