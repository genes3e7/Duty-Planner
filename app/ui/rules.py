"""
app/ui/rules.py

Handles the configuration of scheduling rules (Hard Bans, Soft Bans).
"""

import pandas as pd
import streamlit as st

from app import constants as C
from app.models.config import AppConfig


def render_rules(config: AppConfig) -> None:
    """
    Renders the Rules configuration page.
    """
    st.title("🛡️ Scheduling Rules")
    st.caption("Configure the allowed transitions between shifts (Day N -> Day N+1).")

    if "pending_rules_update" not in st.session_state:
        st.session_state.pending_rules_update = None

    # 1. Prepare Data for Editor
    # Convert nested dict to DataFrame for matrix editing
    # Index: Previous Shift, Columns: Next Shift
    shifts = sorted(list(C.ACTIVE_DUTIES))

    # Load current state (config or pending)
    current_transitions = config.rules.transitions

    # Transform to DataFrame
    data = []
    for prev_shift in shifts:
        row = {"Current Shift": prev_shift}
        for next_shift in shifts:
            val = current_transitions.get(prev_shift, {}).get(next_shift, C.RuleStatus.ALLOWED.value)
            row[next_shift] = val
        data.append(row)

    df = pd.DataFrame(data)

    # 2. Render Data Editor
    st.info("Define strict rules (**Hard Ban**) or discouragements (**Soft Ban**) for consecutive shifts.")

    column_config = {
        "Current Shift": st.column_config.TextColumn("Current (Day N)", disabled=True),
    }

    # Configure options for all shift columns
    options = [s.value for s in C.RuleStatus]
    for s in shifts:
        column_config[s] = st.column_config.SelectboxColumn(
            label=f"To {s} (Day N+1)", options=options, required=True, width="medium"
        )

    edited_df = st.data_editor(
        df, column_config=column_config, hide_index=True, use_container_width=True, key="rules_editor"
    )

    # 3. Process Updates
    if not edited_df.equals(df):
        # Transform back to Dict
        new_transitions = {}
        for _, row in edited_df.iterrows():
            p_shift = row["Current Shift"]
            new_transitions[p_shift] = {}
            for n_shift in shifts:
                new_transitions[p_shift][n_shift] = row[n_shift]

        # Update Config in Session State
        config.rules.transitions = new_transitions
        st.toast("Rules updated temporarily!", icon="🛡️")
        st.rerun()

    st.divider()
    st.markdown("### Legend")
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"**✅ {C.RuleStatus.ALLOWED.value}**: Transition is completely fine.")
    c2.markdown(f"**⚠️ {C.RuleStatus.SOFT.value}**: Avoid if possible, but allowed to solve.")
    c3.markdown(f"**⛔ {C.RuleStatus.HARD.value}**: Strictly forbidden.")
