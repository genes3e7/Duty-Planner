import calendar

import pandas as pd
import streamlit as st

from app import constants as C
from app import logic


def render_planner(sel_year: int, sel_month: int, sel_month_name: str):
    """Renders the main planning grid and actions."""

    if st.session_state.roster_df is None:
        st.info("👈 Please click 'Load / Reset Grid' in the sidebar to start.")
        return

    # --- STATE HEALER ---
    if not isinstance(st.session_state.roster_df, pd.DataFrame):
        st.warning("⚠️ Data state corruption detected. Auto-healing...")
        r_df, d_df = logic.generate_empty_schedule(sel_year, sel_month, st.session_state.config.personnel)
        st.session_state.roster_df = r_df
        st.session_state.day_config_df = d_df
        st.session_state.loaded_date = (sel_year, sel_month)
        st.rerun()

    # HEADERS
    loaded_year, loaded_month = st.session_state.loaded_date
    loaded_month_name = calendar.month_name[loaded_month]

    st.markdown(f"## 🗓️ Roster for: {loaded_month_name} {loaded_year}")

    if (loaded_year, loaded_month) != (sel_year, sel_month):
        st.warning(
            f"⚠️ **Warning:** You are viewing roster for **{loaded_month_name} {loaded_year}**, "
            f"but sidebar is **{sel_month_name} {sel_year}**. Click 'Load / Reset Grid' to switch."
        )

    # 1. CONFIGURATION EXPANDER
    with st.expander("⚙️ Configuration & Constraints", expanded=False):
        col_cfg1, col_cfg2 = st.columns([1, 1])
        with col_cfg1:
            st.subheader("Day Settings")
            b1, b2 = st.columns(2)
            with b1:
                if st.button("Set All SHIFT", use_container_width=True):
                    st.session_state.day_config_df["Mode"] = C.ScheduleMode.SHIFT.value
                    st.rerun()
            with b2:
                if st.button("Set All 24H", use_container_width=True):
                    st.session_state.day_config_df["Mode"] = C.ScheduleMode.FULL_24H.value
                    st.rerun()

            st.session_state.day_config_df = st.data_editor(
                st.session_state.day_config_df,
                column_config={
                    "Active": st.column_config.CheckboxColumn("Active?", width="small"),
                    "Mode": st.column_config.SelectboxColumn(
                        "Mode", options=["Shift", "24H"], width="medium", required=True
                    ),
                    "Is_PH": st.column_config.CheckboxColumn("PH", width="small", disabled=False),
                    "Is_Weekend": st.column_config.CheckboxColumn("Wknd", width="small", disabled=True),
                },
                disabled=["Date", "Day", "Is_Weekend"],
                use_container_width=True,
                height=300,
                key="day_config_editor",
            )

        with col_cfg2:
            st.subheader("Bulk Constraint Upload")
            c_file = st.file_uploader("Upload Excel", type=["xlsx"], key="c_up")
            if c_file and st.button("Merge Constraints", type="primary"):
                try:
                    udf = pd.read_excel(c_file)
                    if "Name" in udf.columns:
                        udf.set_index("Name", inplace=True)
                        count = 0
                        for p in st.session_state.roster_df.index:
                            if p in udf.index:
                                for d_col in st.session_state.roster_df.columns:
                                    day_num = logic.get_day_num(d_col)
                                    val = None
                                    if day_num in udf.columns:
                                        val = udf.at[p, day_num]
                                    elif str(day_num) in udf.columns:
                                        val = udf.at[p, str(day_num)]

                                    if val is not None and pd.notna(val) and str(val).strip() != "":
                                        st.session_state.roster_df.at[p, d_col] = str(val)
                                        count += 1
                        st.success(f"Merged {count} cells!")
                        st.rerun()
                    else:
                        st.error("Uploaded file missing 'Name' column.")
                except Exception as e:
                    st.error(f"Error: {e}")

    # 2. ROSTER GRID PREPARATION
    roster_cols = {}
    for col_name in st.session_state.roster_df.columns:
        day_num = logic.get_day_num(col_name)
        mode = st.session_state.day_config_df.loc[day_num, "Mode"]

        opts = ["", "X", "24H", "S/B"] if mode == C.ScheduleMode.FULL_24H.value else ["", "X", "AM", "PM", "S/B"]

        roster_cols[col_name] = st.column_config.SelectboxColumn(
            label=str(day_num), options=opts, width="small", required=False
        )

    # --- DEFENSIVE CALLBACK FUNCTION ---
    def commit_edits():
        edited = st.session_state["roster_editor"]
        if isinstance(edited, pd.DataFrame):
            edited.columns = edited.columns.astype(str)
            st.session_state.roster_df = edited

    # 3. ROSTER GRID RENDER
    st.data_editor(
        st.session_state.roster_df,
        column_config=roster_cols,
        use_container_width=True,
        height=500,
        key="roster_editor",
        on_change=commit_edits,
    )

    # 4. ACTIONS & STATS
    st.divider()
    st.subheader("Actions")
    act_c1, act_c2, act_c3 = st.columns([1, 1, 2])

    with act_c1:
        if st.button("🧹 Clear Duties Only", help="Removes AM/PM/24H/SB. Keeps 'X'.", use_container_width=True):
            st.session_state.roster_df = logic.clear_schedule(st.session_state.roster_df, clear_constraints=False)
            st.rerun()

    with act_c2:
        if st.button("💥 Clear All Cells", help="Resets entire grid to empty.", use_container_width=True):
            st.session_state.roster_df = logic.clear_schedule(st.session_state.roster_df, clear_constraints=True)
            st.rerun()

    with act_c3:
        if st.button("🚀 GENERATE FILL", type="primary", use_container_width=True):
            with st.spinner("Solving..."):
                res = logic.run_solver(
                    loaded_year,
                    loaded_month,
                    st.session_state.roster_df,
                    st.session_state.day_config_df,
                    st.session_state.config,
                    st.session_state.prev_balance,
                )
                if res:
                    sched, _ = res
                    for (p, d), s in sched.items():
                        st.session_state.roster_df.at[p, f"D{d}"] = s
                    st.success("Solved successfully!")
                    st.rerun()
                else:
                    st.error("No solution found. Check constraints.")

    st.divider()

    stats_df = logic.calculate_stats(
        st.session_state.roster_df,
        st.session_state.day_config_df,
        st.session_state.config,
        st.session_state.prev_balance,
    )

    st.subheader("Statistics & Export")
    c_stat, c_down = st.columns([3, 1])

    with c_stat:
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Pts", f"{stats_df['Month Pts'].sum():.1f}")
        m2.metric("Avg Pts", f"{stats_df['Month Pts'].mean():.2f}")
        m3.metric("Std Dev", f"{stats_df['Month Pts'].std():.2f}")

    with c_down:
        xlsx = logic.export_to_excel_bytes(st.session_state.roster_df, stats_df, st.session_state.config)
        st.download_button(
            label="📥 Download Excel",
            data=xlsx,
            file_name=f"Duty_Plan_{loaded_year}_{loaded_month}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with st.expander("Detailed Stats Table", expanded=True):
        st.dataframe(stats_df, hide_index=True, use_container_width=True)
