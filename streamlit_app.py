import streamlit as st

from app import constants as C
from app.core.data import DataManager
from app.ui.planner import render_planner
from app.ui.settings import render_settings
from app.ui.sidebar import render_sidebar

# Page Configuration
st.set_page_config(page_title=C.APP_TITLE, page_icon="📅", layout="wide", initial_sidebar_state="expanded")

# --- Session State Initialization ---
if "config" not in st.session_state:
    st.session_state.config = DataManager.load_config()
if "prev_balance" not in st.session_state:
    st.session_state.prev_balance = {}
if "roster_df" not in st.session_state:
    st.session_state.roster_df = None
if "day_config_df" not in st.session_state:
    st.session_state.day_config_df = None
if "loaded_date" not in st.session_state:
    st.session_state.loaded_date = None

# --- Sidebar ---
# Capture selection to pass into the planner
sel_year, sel_month, sel_month_name = render_sidebar()

# --- Tabs ---
t1, t2 = st.tabs(["Planner", "Settings"])

with t1:
    render_planner(sel_year, sel_month, sel_month_name)

with t2:
    render_settings()
