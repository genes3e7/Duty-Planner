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
        st.warning(f"⚠️ Data state corruption detected (Type: {type(st.session_state.roster_df)}). Auto-healing...")
        r_df, d_df = logic.generate_empty_schedule(sel_year, sel_month, st.session_state.config.personnel)
        st.session_state.roster_df = r_df
        st.session_state.day_config_df = d_df
        st.session_state.loaded_date = (sel_year, sel_month)
        st.rerun()

    # --- VERSION CONTROL FOR EDITOR ---
    # We use a version number to dynamically change the key of the data_editor.
    # This forces Streamlit to destroy and recreate the widget when we want a hard reset (like Clearing).
    if "roster_version" not in st.session_state:
        st.session_state.roster_version = 0

    # Construct the dynamic key for this render cycle
    editor_key = f"roster_editor_{st.session_state.roster_version}"

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
            # Fix: Using width="stretch" as requested by logs
            with b1:
                if st.button("Set All SHIFT", width="stretch"):
                    st.session_state.day_config_df["Mode"] = C.ScheduleMode.SHIFT.value
                    st.rerun()
            with b2:
                if st.button("Set All 24H", width="stretch"):
                    st.session_state.day_config_df["Mode"] = C.ScheduleMode.FULL_24H.value
                    st.rerun()

            # Capture return value to update state immediately if needed
            edited_day_config = st.data_editor(
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
                width="stretch",
                height=300,
                key="day_config_editor",
            )
            # Sync edits back to session state
            st.session_state.day_config_df = edited_day_config

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
                        st.session_state.roster_version += 1  # Force refresh to show merged data
                        st.rerun()
                    else:
                        st.error("Uploaded file missing 'Name' column.")
                except Exception as e:
                    st.error(f"Error: {e}")

    # 2. ROSTER GRID PREPARATION
    roster_cols = {}
    for col_name in st.session_state.roster_df.columns:
        day_num = logic.get_day_num(col_name)

        # Skip columns that aren't valid days (e.g. index/metadata cols if any slipped in)
        if day_num <= 0 or day_num not in st.session_state.day_config_df.index:
            continue

        mode = st.session_state.day_config_df.loc[day_num, "Mode"]

        opts = ["", "X", "24H", "S/B"] if mode == C.ScheduleMode.FULL_24H.value else ["", "X", "AM", "PM", "S/B"]

        roster_cols[col_name] = st.column_config.SelectboxColumn(
            label=str(day_num), options=opts, width="small", required=False
        )

    # --- CALLBACK: SYNC STATE BEFORE RERUN ---
    # This prevents the 'double-entry' bug by ensuring state is updated
    # immediately when the editor triggers a change event.
    def commit_edits():
        if editor_key in st.session_state:
            edited = st.session_state[editor_key]
            # Verify we have a dataframe to avoid the dict error
            if isinstance(edited, pd.DataFrame):
                st.session_state.roster_df = edited

    # 3. ROSTER GRID RENDER
    st.data_editor(
        st.session_state.roster_df,
        column_config=roster_cols,
        width="stretch",
        height=500,
        key=editor_key,  # Dynamic Key
        on_change=commit_edits,  # Re-enabled callback
    )

    # 4. ACTIONS & STATS
    st.divider()
    st.subheader("Actions")
    act_c1, act_c2, act_c3 = st.columns([1, 1, 2])

    with act_c1:
        if st.button("🧹 Clear Duties Only", help="Removes AM/PM/24H/SB. Keeps 'X'.", width="stretch"):
            if isinstance(st.session_state.roster_df, pd.DataFrame):
                # on_change callback has already synced the state, so we can just call logic
                st.session_state.roster_df = logic.clear_schedule(st.session_state.roster_df, clear_constraints=False)
                st.session_state.roster_version += 1
                st.rerun()
            else:
                st.error(f"Critical Error: Roster data is {type(st.session_state.roster_df)}, expected DataFrame.")

    with act_c2:
        if st.button("💥 Clear All Cells", help="Resets entire grid to empty.", width="stretch"):
            if isinstance(st.session_state.roster_df, pd.DataFrame):
                st.session_state.roster_df = logic.clear_schedule(st.session_state.roster_df, clear_constraints=True)
                st.session_state.roster_version += 1
                st.rerun()
            else:
                st.error("Critical Error: Roster data corrupted.")

    with act_c3:
        if st.button("🚀 GENERATE FILL", type="primary", width="stretch"):
            with st.spinner("Solving..."):
                if isinstance(st.session_state.roster_df, pd.DataFrame):
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
                        st.session_state.roster_version += 1
                        st.success("Solved successfully!")
                        st.rerun()
                    else:
                        st.error("No solution found. Check constraints.")
                else:
                    st.error("Data error. Please reload grid.")

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
            width="stretch",
        )

    with st.expander("Detailed Stats Table", expanded=True):
        st.dataframe(stats_df, hide_index=True, width="stretch")
