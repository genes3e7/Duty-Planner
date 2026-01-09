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
            pts_sb = st.number_input("Pts: S/B", value=cfg.points.SB)

        st.divider()
        st.subheader("Multipliers & Logic")

        # Row 1: Weekend & PH
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

        # Row 2: Friday & PH Eve (New)
        st.caption("Special Day Logic")
        m3, m4 = st.columns(2)
        with m3:
            fri_mult = st.number_input("Friday Value", value=cfg.points.friday_multiplier)
            fri_is_mult = st.toggle("Friday uses Multiplier?", value=cfg.points.friday_is_multiplier)
        with m4:
            eve_mult = st.number_input("PH Eve Value", value=cfg.points.ph_eve_multiplier)
            eve_is_mult = st.toggle("PH Eve uses Multiplier?", value=cfg.points.ph_eve_is_multiplier)

        st.subheader("Personnel")
        ppl_str = st.text_area("Names (comma separated)", value=", ".join(cfg.personnel))

        if st.form_submit_button("💾 Save Settings"):
            # Clean and deduplicate names
            new_personnel = sorted(list(set([x.strip() for x in ppl_str.split(",") if x.strip()])))

            # Validation: Ensure list is not empty
            if not new_personnel:
                st.error("Personnel list cannot be empty. Please add at least one name.")
                return

            # Update Configuration object only on submit
            cfg.constraints.personnel_needed_per_shift["AM"] = am_req
            cfg.constraints.personnel_needed_per_shift["PM"] = pm_req
            cfg.constraints.personnel_needed_per_shift["24H"] = h24_req
            cfg.constraints.standby_per_day = sb_req

            cfg.points.AM = pts_am
            cfg.points.PM = pts_pm
            cfg.points.FULL_24H = pts_24h
            cfg.points.SB = pts_sb

            cfg.points.weekend_multiplier = wk_mult
            cfg.points.weekend_is_multiplier = wk_is_mult
            cfg.points.ph_multiplier = ph_mult
            cfg.points.ph_is_multiplier = ph_is_mult

            cfg.points.friday_multiplier = fri_mult
            cfg.points.friday_is_multiplier = fri_is_mult
            cfg.points.ph_eve_multiplier = eve_mult
            cfg.points.ph_eve_is_multiplier = eve_is_mult

            cfg.personnel = new_personnel

            # Sync Roster DataFrame with new names if it exists
            if "roster_df" in st.session_state and isinstance(st.session_state.roster_df, pd.DataFrame):
                st.session_state.roster_df = logic.synchronize_roster_index(st.session_state.roster_df, new_personnel)

            if DataManager.save_config(cfg):
                st.session_state.config = cfg
                # User requested a clear/slower notification.
                # st.success persists until user interaction or next rerun.
                st.success("✅ Settings Saved Successfully! Roster updated.")
                # We do NOT rerun immediately here to let the user see the success message.
                # The state is updated, so if they navigate away or click something else, it will stick.
            else:
                st.error("Failed to save settings. Check logs.")
