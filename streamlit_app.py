import streamlit as st
import pandas as pd
import calendar
import os
import datetime
from app import constants as C
from app import logic

# Page Configuration
st.set_page_config(
    page_title=C.APP_TITLE, 
    page_icon="📅", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Session State Initialization ---
if "config" not in st.session_state:
    st.session_state.config = logic.DataManager.load_config()
if "prev_balance" not in st.session_state:
    st.session_state.prev_balance = {}
if "roster_df" not in st.session_state:
    st.session_state.roster_df = None
if "day_config_df" not in st.session_state:
    st.session_state.day_config_df = None
if "loaded_date" not in st.session_state:
    st.session_state.loaded_date = None 

# --- Sidebar: Global Controls ---
with st.sidebar:
    st.title("Duty Planner")
    
    # Date Picker
    try:
        default_date = datetime.date(st.session_state.config.year, st.session_state.config.month, 1)
    except:
        default_date = datetime.date.today().replace(day=1)

    sel_date = st.date_input(
        "Select Planning Month", 
        value=default_date, 
        min_value=datetime.date(2000, 1, 1),
        help="Pick any day in the month you want to plan for."
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
            try:
                with open("temp_import.xlsx", "wb") as f:
                    f.write(up_file.getbuffer())
                
                prev = logic.DataManager.load_previous_balance("temp_import.xlsx")
                st.session_state.prev_balance = prev
                
                if st.button("Update Personnel List?"):
                    st.session_state.config.personnel = sorted(list(prev.keys()))
                    st.rerun()
                
                if os.path.exists("temp_import.xlsx"):
                    os.remove("temp_import.xlsx")
                st.success(f"Imported {len(prev)} records!")
            except Exception as e:
                st.error(f"Error: {e}")

# --- Tab 1: Planner ---
def render_planner():
    if st.session_state.roster_df is None:
        st.info("👈 Please click 'Load / Reset Grid' in the sidebar to start.")
        return

    # --- SILENT SANITIZER ---
    # Force columns to string inplace. NO RERUN.
    # This fixes the input side of the "Alternate Update" bug.
    if not all(isinstance(c, str) for c in st.session_state.roster_df.columns):
        st.session_state.roster_df.columns = st.session_state.roster_df.columns.astype(str)

    # MAIN UI
    loaded_year, loaded_month = st.session_state.loaded_date
    loaded_month_name = calendar.month_name[loaded_month]
    
    st.markdown(f"## 🗓️ Roster for: {loaded_month_name} {loaded_year}")
    
    if (loaded_year, loaded_month) != (sel_year, sel_month):
        st.warning(f"⚠️ **Warning:** You are viewing the roster for **{loaded_month_name} {loaded_year}**, but the sidebar selection is **{sel_month_name} {sel_year}**. Click 'Load / Reset Grid' to switch.")

    # 1. CONFIGURATION
    with st.expander("⚙️ Configuration & Constraints (Day Settings / Bulk Upload)", expanded=False):
        col_cfg1, col_cfg2 = st.columns([1, 1])
        
        with col_cfg1:
            st.subheader("Day Settings")
            st.caption("Toggle PH, set Modes, or Disable days.")
            b1, b2 = st.columns(2)
            with b1:
                if st.button("Set All SHIFT", use_container_width=True):
                    st.session_state.day_config_df["Mode"] = C.ScheduleMode.SHIFT.value
                    st.rerun()
            with b2:
                if st.button("Set All 24H", use_container_width=True):
                    st.session_state.day_config_df["Mode"] = C.ScheduleMode.FULL_24H.value
                    st.rerun()

            edited_days = st.data_editor(
                st.session_state.day_config_df,
                column_config={
                    "Active": st.column_config.CheckboxColumn("Active?", width="small"),
                    "Mode": st.column_config.SelectboxColumn("Mode", options=["Shift", "24H"], width="medium", required=True),
                    "Is_PH": st.column_config.CheckboxColumn("PH", width="small", disabled=False), 
                    "Is_Weekend": st.column_config.CheckboxColumn("Wknd", width="small", disabled=True)
                },
                disabled=["Date", "Day", "Is_Weekend"],
                use_container_width=True,
                height=300
            )
            st.session_state.day_config_df = edited_days

        with col_cfg2:
            st.subheader("Bulk Constraint Upload")
            st.caption("Upload Excel with 'Name' column + Day columns (1, 2...)")
            c_file = st.file_uploader("Upload Excel", type=["xlsx"], key="c_up")
            if c_file and st.button("Merge Constraints", type="primary"):
                try:
                    udf = pd.read_excel(c_file)
                    if "Name" in udf.columns:
                        udf.set_index("Name", inplace=True)
                        count = 0
                        for p in st.session_state.roster_df.index:
                            if p in udf.index:
                                for d in st.session_state.roster_df.columns:
                                    val = None
                                    if d in udf.columns: val = udf.at[p, d]
                                    elif str(d) in udf.columns: val = udf.at[p, str(d)]
                                    elif int(d) in udf.columns: val = udf.at[p, int(d)]
                                    
                                    if val is not None and pd.notna(val) and str(val).strip() != "":
                                        st.session_state.roster_df.at[p, d] = str(val)
                                        count += 1
                        st.success(f"Merged {count} cells!")
                        st.rerun()
                    else:
                        st.error("Uploaded file missing 'Name' column.")
                except Exception as e:
                    st.error(f"Error: {e}")

    # 2. ROSTER GRID
    
    # Configure Columns
    roster_cols = {}
    for col_name in st.session_state.roster_df.columns:
        # col_name is guaranteed string now
        day_num = int(col_name) 
        mode = st.session_state.day_config_df.loc[day_num, "Mode"]
        
        if mode == C.ScheduleMode.FULL_24H.value:
            opts = ["", "X", "24H", "S/B"]
        else:
            opts = ["", "X", "AM", "PM", "S/B"]
            
        roster_cols[col_name] = st.column_config.SelectboxColumn(
            label=col_name,
            options=opts,
            width="small",
            required=False
        )

    # RENDER EDITOR
    edited_roster = st.data_editor(
        st.session_state.roster_df,
        column_config=roster_cols,
        use_container_width=True,
        height=500
    )
    
    # --- OUTPUT SANITIZATION ---
    # Fix the output side of the "Alternate Update" bug.
    # If pandas auto-detected Int columns, convert them back to Str immediately.
    if edited_roster is not None:
        edited_roster.columns = edited_roster.columns.astype(str)
        st.session_state.roster_df = edited_roster

    # 3. ACTIONS
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
                    st.session_state.prev_balance
                )
                if res:
                    sched, _ = res
                    # Write back securely
                    for (p, d), s in sched.items():
                        st.session_state.roster_df.at[p, str(d)] = s
                    st.success("Solved successfully!")
                    st.rerun()
                else:
                    st.error("No solution found. Check constraints.")

    st.divider()
    
    # STATS & EXPORT
    stats_df = logic.calculate_stats(
        st.session_state.roster_df, 
        st.session_state.day_config_df, 
        st.session_state.config, 
        st.session_state.prev_balance
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
            use_container_width=True
        )

    with st.expander("Detailed Stats Table", expanded=True):
        st.dataframe(stats_df, hide_index=True, use_container_width=True)

# --- Tab 2: Settings ---
def render_settings():
    st.header("Settings")
    cfg = st.session_state.config

    with st.form("settings_form"):
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Manpower Requirements")
            cfg.constraints.personnel_needed_per_shift["AM"] = st.number_input("AM Req", 0, value=cfg.constraints.personnel_needed_per_shift.get("AM", 1))
            cfg.constraints.personnel_needed_per_shift["PM"] = st.number_input("PM Req", 0, value=cfg.constraints.personnel_needed_per_shift.get("PM", 1))
            cfg.constraints.personnel_needed_per_shift["24H"] = st.number_input("24H Req", 0, value=cfg.constraints.personnel_needed_per_shift.get("24H", 1))
            cfg.constraints.standby_per_day = st.number_input("Standby Req", 0, value=cfg.constraints.standby_per_day)

        with c2:
            st.subheader("Scoring Values")
            cfg.points.AM = st.number_input("Pts: AM", value=cfg.points.AM)
            cfg.points.PM = st.number_input("Pts: PM", value=cfg.points.PM)
            cfg.points.FULL_24H = st.number_input("Pts: 24H", value=cfg.points.FULL_24H)

        st.divider()
        st.subheader("Multipliers & Logic")
        m1, m2 = st.columns(2)
        with m1:
            cfg.points.ph_multiplier = st.number_input("PH Value", value=cfg.points.ph_multiplier)
            cfg.points.ph_is_multiplier = st.toggle("PH uses Multiplier?", value=cfg.points.ph_is_multiplier, help="On = Multiply base points. Off = Add this value to base points.")
        with m2:
            cfg.points.weekend_multiplier = st.number_input("Weekend Value", value=cfg.points.weekend_multiplier)
            cfg.points.weekend_is_multiplier = st.toggle("Weekend uses Multiplier?", value=cfg.points.weekend_is_multiplier)

        st.subheader("Personnel")
        ppl_str = st.text_area("Names (comma separated)", value=", ".join(cfg.personnel))

        if st.form_submit_button("💾 Save Settings"):
            cfg.personnel = sorted(list(set([x.strip() for x in ppl_str.split(",") if x.strip()])))
            logic.DataManager.save_config(cfg)
            st.session_state.config = cfg
            st.success("Settings Saved!")
            st.rerun()

# --- Main App Entry Point ---
t1, t2 = st.tabs(["Planner", "Settings"])
with t1:
    render_planner()
with t2:
    render_settings()
