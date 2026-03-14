import streamlit as st
from src.ui.db_utils import get_all_packages
from src.services.analytical_service import AnalyticalService
from src.services.export_service import ExcelExporter

def render_dashboard():
    st.header("Package Dashboard")
    
    # Sidebar for bulk actions
    with st.sidebar:
        st.subheader("Bulk Actions")
        approved_pkgs = get_all_packages(status_filter=["APPROVED"])
        if approved_pkgs:
            st.success(f"Found {len(approved_pkgs)} approved packages.")
            if st.button("Prepare Bulk Export"):
                try:
                    analytical = AnalyticalService()
                    exporter = ExcelExporter()
                    
                    summary_df = analytical.get_summary()
                    transactions_df = analytical.get_transactions()
                    
                    approved_ids = [p.id for p in approved_pkgs]
                    
                    # Filter dataframes for approved packages only
                    filtered_summary = summary_df[summary_df['package_id'].isin(approved_ids)]
                    filtered_transactions = transactions_df[transactions_df['package_id'].isin(approved_ids)]
                    
                    # Rename columns to match ExcelExporter expected names if necessary
                    # ExcelExporter expects: summary_data: List[Dict], transactions_data: List[Dict]
                    # summary_data keys: package_id, filename, lender_name, document_date, total_amount
                    # transactions_data keys: package_id, component, amount
                    
                    # Prepare data for export
                    summary_data = filtered_summary.rename(columns={'effective_date': 'document_date'}).to_dict('records')
                    transactions_data = filtered_transactions.to_dict('records')
                    
                    excel_stream = exporter.generate_excel(summary_data, transactions_data)
                    
                    st.download_button(
                        label="⬇️ Download Approved Excel",
                        data=excel_stream,
                        file_name="approved_packages_export.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except Exception as e:
                    st.error(f"Export failed: {str(e)}")
        else:
            st.info("No approved packages available for export.")

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
