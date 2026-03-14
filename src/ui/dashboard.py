import streamlit as st
from src.ui.db_utils import get_all_packages

def render_dashboard():
    st.header("Package Dashboard")
    
    # Status Filtering
    statuses = ["INGESTED", "EXTRACTED", "APPROVED"]
    selected_statuses = st.multiselect("Filter by Status", statuses, default=statuses)
    
    # Fetch Data
    packages = get_all_packages(status_filter=selected_statuses)
    
    if not packages:
        st.info("No packages found.")
        return

    # Header Row
    cols = st.columns([2, 3, 2, 2, 1])
    cols[0].write("**ID**")
    cols[1].write("**Filename**")
    cols[2].write("**Status**")
    cols[3].write("**Created At**")
    cols[4].write("**Action**")

    # Data Rows
    for pkg in packages:
        cols = st.columns([2, 3, 2, 2, 1])
        # Truncate ID for display
        cols[0].write(f"`{pkg.id[:8]}...`")
        cols[1].write(pkg.original_filename)
        cols[2].write(pkg.status)
        cols[3].write(pkg.created_at.strftime("%Y-%m-%d %H:%M"))
        
        # Action Button
        if cols[4].button("Review", key=f"btn_{pkg.id}"):
            st.session_state.current_package_id = pkg.id
            st.session_state.current_view = "Reviewer"
            st.rerun()
