"""
app/ui/rules.py

Handles the configuration of scheduling rules (Hard Bans, Soft Bans)
and solver constraints (Teams, Limits).
"""

import pandas as pd
import streamlit as st

from app import constants as C
from app.models.config import AppConfig


def _render_constraints_tab(config: AppConfig):
    """Renders the Shift Constraints & Solver Limits."""
    st.caption("Define the staff requirements, team structures, and work limits.")

    # --- 1. Team Configuration ---
    st.markdown("#### 👥 Team Configuration")
    t1, t2 = st.columns(2)
    with t1:
        curr_active = config.constraints.num_active_teams
        new_active = st.number_input(
            "Active Teams",  # Standardized Label
            min_value=1,
            value=curr_active,
            step=1,
            help="1 Team = 1 Set of (AM + PM + 24H). 2 Teams = 2 Sets.",
        )
        if new_active != curr_active:
            if "pending_constraints_updates" not in st.session_state:
                st.session_state.pending_constraints_updates = {}
            st.session_state.pending_constraints_updates["num_active_teams"] = new_active

    with t2:
        curr_sb = config.constraints.num_standby_teams
        new_sb = st.number_input(
            "Standby Teams",  # Standardized Label
            min_value=0,
            value=curr_sb,
            step=1,
            help="Number of independent Standby lines.",
        )
        if new_sb != curr_sb:
            if "pending_constraints_updates" not in st.session_state:
                st.session_state.pending_constraints_updates = {}
            st.session_state.pending_constraints_updates["num_standby_teams"] = new_sb

    st.divider()

    # --- 2. Staff Per Team ---
    st.markdown("#### 👤 Staff per Team")
    st.caption("Staff required for **one single team**.")

    c1, c2, c3, c4 = st.columns(4)
    shifts = [("AM", c1), ("PM", c2), ("24H", c3)]

    for shift_name, col in shifts:
        with col:
            current_val = config.constraints.personnel_needed_per_shift.get(shift_name, 1)
            # Standardized: "{Shift} Staff" instead of "Needed"
            val = int(
                st.number_input(
                    f"{shift_name} Staff",
                    min_value=0,
                    value=current_val,
                    step=1,
                    key=f"rule_constraint_{shift_name}",
                )
            )
            if val != current_val:
                if "pending_constraints_updates" not in st.session_state:
                    st.session_state.pending_constraints_updates = {}
                st.session_state.pending_constraints_updates[shift_name] = val

    with c4:
        val_sb = int(
            st.number_input(
                "Standby Staff",  # Standardized Label
                min_value=0,
                value=config.constraints.standby_per_day,
                step=1,
                key="rule_constraint_sb",
            )
        )
        if val_sb != config.constraints.standby_per_day:
            if "pending_constraints_updates" not in st.session_state:
                st.session_state.pending_constraints_updates = {}
            st.session_state.pending_constraints_updates["standby_per_day"] = val_sb

    st.divider()

    # --- 3. Global Limits ---
    st.markdown("#### 🛑 Global Limits")

    l1, l2, l3 = st.columns(3)

    with l1:
        val_max = int(
            st.number_input(
                "Max Consecutive Days",  # Standardized: "Days" is clearer than "Duties"
                min_value=1,
                value=config.constraints.max_consecutive_duties,
                step=1,
                key="rule_max_consecutive",
            )
        )
        if val_max != config.constraints.max_consecutive_duties:
            if "pending_constraints_updates" not in st.session_state:
                st.session_state.pending_constraints_updates = {}
            st.session_state.pending_constraints_updates["max_consecutive_duties"] = val_max

    with l2:
        val_catch = float(
            st.number_input(
                "Catch-Up Limit",  # Standardized
                min_value=0.0,
                value=float(config.constraints.catch_up_limit),
                step=1.0,
                help="Max points above average allowed to catch up.",
                key="rule_catch_up",
            )
        )
        if val_catch != config.constraints.catch_up_limit:
            if "pending_constraints_updates" not in st.session_state:
                st.session_state.pending_constraints_updates = {}
            st.session_state.pending_constraints_updates["catch_up_limit"] = val_catch

    with l3:
        val_timeout = float(
            st.number_input(
                "Solver Timeout (s)",
                min_value=1.0,
                value=float(config.constraints.solver_timeout_seconds),
                step=5.0,
                key="rule_timeout",
            )
        )
        if val_timeout != config.constraints.solver_timeout_seconds:
            if "pending_constraints_updates" not in st.session_state:
                st.session_state.pending_constraints_updates = {}
            st.session_state.pending_constraints_updates["solver_timeout_seconds"] = val_timeout

    # Apply Logic
    if "pending_constraints_updates" in st.session_state and st.session_state.pending_constraints_updates:
        # Separate nested dict updates from top-level fields
        nested_updates = {}
        top_level_updates = {}

        for k, v in st.session_state.pending_constraints_updates.items():
            if k in ["AM", "PM", "24H"]:
                nested_updates[k] = v
            else:
                top_level_updates[k] = v

        updates = {}
        if nested_updates:
            new_needs = {**config.constraints.personnel_needed_per_shift, **nested_updates}
            updates["personnel_needed_per_shift"] = new_needs

        if top_level_updates:
            updates.update(top_level_updates)

        if updates:
            config.constraints = config.constraints.model_copy(update=updates)
            st.session_state.pending_constraints_updates = {}
            st.rerun()


def _render_transitions_tab(config: AppConfig):
    """Renders the Transition Rules Matrix."""
    st.caption("Configure the allowed transitions between shifts (Day N -> Day N+1).")
    st.info("Define strict rules (**Hard Ban**) or discouragements (**Soft Ban**) for consecutive shifts.")

    shifts = sorted(list(C.ACTIVE_DUTIES))
    current_transitions = config.rules.transitions

    data = []
    for prev_shift in shifts:
        row = {"Current Shift": prev_shift}
        for next_shift in shifts:
            val = current_transitions.get(prev_shift, {}).get(next_shift, C.RuleStatus.ALLOWED.value)
            row[next_shift] = val
        data.append(row)

    df = pd.DataFrame(data)

    column_config = {
        "Current Shift": st.column_config.TextColumn("Current (Day N)", disabled=True),
    }

    options = [s.value for s in C.RuleStatus]
    for s in shifts:
        column_config[s] = st.column_config.SelectboxColumn(
            label=f"To {s}", options=options, required=True, width="medium"
        )

    edited_df = st.data_editor(
        df, column_config=column_config, hide_index=True, width="stretch", key="rules_trans_editor"
    )

    if not edited_df.equals(df):
        new_transitions = {}
        for _, row in edited_df.iterrows():
            p_shift = row["Current Shift"]
            new_transitions[p_shift] = {}
            for n_shift in shifts:
                new_transitions[p_shift][n_shift] = row[n_shift]

        config.rules.transitions = new_transitions
        st.toast("Rules updated!", icon="🛡️")
        st.rerun()

    st.markdown("### Legend")
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"**✅ {C.RuleStatus.ALLOWED.value}**: Allowed.")
    c2.markdown(f"**⚠️ {C.RuleStatus.SOFT.value}**: Avoid.")
    c3.markdown(f"**⛔ {C.RuleStatus.HARD.value}**: Forbidden.")


def render_rules(config: AppConfig) -> None:
    """
    Renders the Rules configuration page.
    """
    st.title("🛡️ Rules & Constraints")

    tab1, tab2 = st.tabs(["📋 Configuration", "🔄 Transitions"])

    with tab1:
        _render_constraints_tab(config)

    with tab2:
        _render_transitions_tab(config)
