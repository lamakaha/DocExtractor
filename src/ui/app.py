import streamlit as st
from src.ui.dashboard import render_dashboard
from src.ui.reviewer import show_reviewer

# Page config
st.set_page_config(
    page_title="DocExtractor - Human-In-The-Loop Reviewer",
    layout="wide",
)

# Initialize session state
if 'current_view' not in st.session_state:
    st.session_state.current_view = 'Dashboard'
if 'current_package_id' not in st.session_state:
    st.session_state.current_package_id = None

# Sidebar navigation
st.sidebar.title("DocExtractor")
navigation = st.sidebar.radio("Navigation", ["Dashboard", "Reviewer"], 
                              index=0 if st.session_state.current_view == 'Dashboard' else 1)

# Sync sidebar with session state
if navigation != st.session_state.current_view:
    st.session_state.current_view = navigation

# Main view routing
if st.session_state.current_view == "Dashboard":
    render_dashboard()
elif st.session_state.current_view == "Reviewer":
    if st.session_state.current_package_id:
        show_reviewer(st.session_state.current_package_id)
    else:
        st.header("Reviewer")
        st.warning("Please select a package from the Dashboard to review.")
