import pandas as pd
import streamlit as st

from app import logic
from app.core.data import DataManager


def render_settings():
    st.header("Settings")
    cfg = st.session_state.config

    with st.form("settings_form"):
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Manpower Requirements")
            # Added max bounds to inputs
            am_req = st.number_input("AM Req", 0, 20, value=cfg.constraints.personnel_needed_per_shift.get("AM", 1))
            pm_req = st.number_input("PM Req", 0, 20, value=cfg.constraints.personnel_needed_per_shift.get("PM", 1))
            h24_req = st.number_input("24H Req", 0, 20, value=cfg.constraints.personnel_needed_per_shift.get("24H", 1))
            sb_req = st.number_input("Standby Req", 0, 20, value=cfg.constraints.standby_per_day)

        with c2:
            st.subheader("Scoring Values")
            pts_am = st.number_input("Pts: AM", value=cfg.points.AM)
            pts_pm = st.number_input("Pts: PM", value=cfg.points.PM)
            pts_24h = st.number_input("Pts: 24H", value=cfg.points.FULL_24H)

        st.divider()
        st.subheader("Multipliers & Logic")
        m1, m2 = st.columns(2)
        with m1:
            wk_mult = st.number_input("Weekend Value", value=cfg.points.weekend_multiplier)
            wk_is_mult = st.toggle("Weekend uses Multiplier?", value=cfg.points.weekend_is_multiplier)

        with m2:
            ph_mult = st.number_input("PH Value", value=cfg.points.ph_multiplier)
            ph_is_mult = st.toggle(
                "PH uses Multiplier?",
                value=cfg.points.ph_is_multiplier,
                help="On = Multiply base points. Off = Add this value to base points.",
            )

        st.subheader("Personnel")
        ppl_str = st.text_area("Names (comma separated)", value=", ".join(cfg.personnel))

        if st.form_submit_button("💾 Save Settings"):
            # Preserve order while deduplicating
            seen = set()
            new_personnel = []
            for name in ppl_str.split(","):
                name = name.strip()
                if name and name not in seen:
                    seen.add(name)
                    new_personnel.append(name)

            # Validation: Ensure list is not empty
            if not new_personnel:
                st.error("Personnel list cannot be empty. Please add at least one name.")
                return

            # Work on a deep copy to prevent partial mutations on failure
            cfg_copy = cfg.model_copy(deep=True)

            # Update Configuration object on the copy
            # Explicitly cast inputs to ensure correct types
            cfg_copy.constraints.personnel_needed_per_shift["AM"] = int(am_req)
            cfg_copy.constraints.personnel_needed_per_shift["PM"] = int(pm_req)
            cfg_copy.constraints.personnel_needed_per_shift["24H"] = int(h24_req)
            cfg_copy.constraints.standby_per_day = int(sb_req)

            cfg_copy.points.AM = float(pts_am)
            cfg_copy.points.PM = float(pts_pm)
            cfg_copy.points.FULL_24H = float(pts_24h)

            cfg_copy.points.weekend_multiplier = float(wk_mult)
            cfg_copy.points.weekend_is_multiplier = wk_is_mult
            cfg_copy.points.ph_multiplier = float(ph_mult)
            cfg_copy.points.ph_is_multiplier = ph_is_mult

            cfg_copy.personnel = new_personnel

            # Sync Roster DataFrame with new names if it exists
            new_roster_df = None
            if "roster_df" in st.session_state and isinstance(st.session_state.roster_df, pd.DataFrame):
                new_roster_df = logic.synchronize_roster_index(st.session_state.roster_df, new_personnel)

            # Attempt Save
            if DataManager.save_config(cfg_copy):
                # Only update session state on success
                st.session_state.config = cfg_copy
                if new_roster_df is not None:
                    st.session_state.roster_df = new_roster_df

                st.success("Settings Saved! Roster updated.")
                st.rerun()
            else:
                st.error("Failed to save settings. Check logs.")
