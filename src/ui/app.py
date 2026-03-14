import os
import streamlit as st
from dotenv import load_dotenv

# Load environment variables early
load_dotenv()

# Page config
st.set_page_config(
    page_title="DocExtractor - Human-In-The-Loop Reviewer",
    layout="wide",
)

# Early check for OpenRouter API Key
if not os.getenv("OPENROUTER_API_KEY") and not os.getenv("GEMINI_API_KEY"):
    st.title("DocExtractor")
    st.error("🔑 **OPENROUTER_API_KEY is not set.**")
    st.info("""
    To use this application, you need an OpenRouter API Key.
    
    1. Create a file named `.env` in the project root directory.
    2. Add the following line to the file:
       ```
       OPENROUTER_API_KEY=your_actual_api_key_here
       GEMINI_MODEL=google/gemini-2.0-flash-001
       ```
    3. Restart the Streamlit application.
    
    *Note: You can use `.env.example` as a template.*
    """)
    st.stop()

from src.ui.dashboard import render_dashboard
from src.ui.reviewer import show_reviewer

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
