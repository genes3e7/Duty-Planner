import streamlit as st

from app.core.data import DataManager


def render_settings():
    st.header("Settings")
    cfg = st.session_state.config

    with st.form("settings_form"):
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Manpower Requirements")
            cfg.constraints.personnel_needed_per_shift["AM"] = st.number_input(
                "AM Req", 0, value=cfg.constraints.personnel_needed_per_shift.get("AM", 1)
            )
            cfg.constraints.personnel_needed_per_shift["PM"] = st.number_input(
                "PM Req", 0, value=cfg.constraints.personnel_needed_per_shift.get("PM", 1)
            )
            cfg.constraints.personnel_needed_per_shift["24H"] = st.number_input(
                "24H Req", 0, value=cfg.constraints.personnel_needed_per_shift.get("24H", 1)
            )
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
            cfg.points.weekend_multiplier = st.number_input("Weekend Value", value=cfg.points.weekend_multiplier)
            cfg.points.weekend_is_multiplier = st.toggle(
                "Weekend uses Multiplier?", value=cfg.points.weekend_is_multiplier
            )

        with m2:
            cfg.points.ph_multiplier = st.number_input("PH Value", value=cfg.points.ph_multiplier)
            cfg.points.ph_is_multiplier = st.toggle(
                "PH uses Multiplier?",
                value=cfg.points.ph_is_multiplier,
                help="On = Multiply base points. Off = Add this value to base points.",
            )

        st.subheader("Personnel")
        ppl_str = st.text_area("Names (comma separated)", value=", ".join(cfg.personnel))

        if st.form_submit_button("💾 Save Settings"):
            cfg.personnel = sorted(list(set([x.strip() for x in ppl_str.split(",") if x.strip()])))
            if DataManager.save_config(cfg):
                st.session_state.config = cfg
                st.success("Settings Saved!")
                st.rerun()
            else:
                st.error("Failed to save settings. Check logs.")
