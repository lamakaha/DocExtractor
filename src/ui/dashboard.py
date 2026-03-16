import os
import streamlit as st
import pandas as pd
from src.ui.db_utils import (
    get_all_packages, 
    get_package_logs, 
    get_latest_extraction_job,
    parse_log_details,
    archive_multiple_packages, 
    archive_package
)
from src.services.analytical_service import AnalyticalService
from src.services.export_service import ExcelExporter
from src.ui.watcher_manager import start_watcher, stop_watcher, is_watcher_running

def format_log_metadata(details):
    if not isinstance(details, dict):
        return str(details) if details else ""
    parts = []
    if details.get("model_id"):
        parts.append(f"model={details['model_id']}")
    if details.get("prompt_version"):
        parts.append(f"prompt={details['prompt_version']}")
    if details.get("latency_ms") is not None:
        parts.append(f"latency={details['latency_ms']}ms")
    usage = details.get("usage")
    if isinstance(usage, dict) and usage.get("total_tokens") is not None:
        parts.append(f"tokens={usage['total_tokens']}")
    if details.get("content_items") is not None:
        parts.append(f"items={details['content_items']}")
    if details.get("page_number") is not None:
        parts.append(f"page={details['page_number']}")
    return " | ".join(parts)

def format_failure_diagnostic(details, job):
    parts = []
    if isinstance(details, dict) and details.get("error"):
        parts.append(f"error={details['error']}")
    if isinstance(details, dict) and details.get("last_error"):
        parts.append(f"last_error={details['last_error']}")
    if job is not None:
        parts.append(f"job={job.status} {job.attempts}/{job.max_attempts}")
        if job.last_error:
            parts.append(f"job_error={job.last_error}")
    return " | ".join(parts)

def build_log_rows(logs, latest_job=None):
    rows = []
    for log in logs:
        level_icon = "ℹ️"
        if log.level == "ERROR":
            level_icon = "❌"
        elif log.level == "WARNING":
            level_icon = "⚠️"
        elif log.level == "SUCCESS":
            level_icon = "✅"

        details = parse_log_details(log.details)
        rows.append(
            {
                "Time": log.timestamp.strftime("%H:%M:%S"),
                "Stage": log.stage,
                "Status": f"{level_icon} {log.level}",
                "Message": log.message,
                "Metadata": format_log_metadata(details),
                "Diagnostics": format_failure_diagnostic(details, latest_job if log.level in {"ERROR", "WARNING"} else None),
            }
        )
    return rows

def build_observability_metrics(summary_df):
    if summary_df is None or summary_df.empty:
        return []
    summary = summary_df.iloc[0].to_dict()
    return [
        {"label": "Errors", "value": int(summary.get("error_logs") or 0)},
        {"label": "Retries", "value": int(summary.get("retrying_jobs") or 0)},
        {
            "label": "Avg Latency",
            "value": "N/A" if summary.get("avg_latency_ms") is None else f"{summary['avg_latency_ms']:.1f}ms",
        },
        {
            "label": "Avg Tokens",
            "value": "N/A" if summary.get("avg_total_tokens") is None else f"{summary['avg_total_tokens']:.0f}",
        },
    ]

def build_recent_failure_rows(failures_df):
    if failures_df is None or failures_df.empty:
        return []
    rows = []
    for _, failure in failures_df.iterrows():
        job_status = failure.get("job_status")
        attempts = failure.get("attempts")
        max_attempts = failure.get("max_attempts")
        retry_text = ""
        if pd.notna(attempts) and pd.notna(max_attempts):
            retry_text = f"{int(attempts)}/{int(max_attempts)}"
        rows.append(
            {
                "Time": failure["timestamp"].strftime("%Y-%m-%d %H:%M") if hasattr(failure["timestamp"], "strftime") else str(failure["timestamp"]),
                "Package": str(failure["package_id"])[:8],
                "Stage": failure["stage"],
                "Level": failure["level"],
                "Message": failure["message"],
                "Job": job_status or "",
                "Attempts": retry_text,
                "Error": failure.get("last_error") or "",
            }
        )
    return rows

def render_dashboard():
    st.header("Package Dashboard")
    
    # Initialize selection in session state if not present
    if "selected_packages" not in st.session_state:
        st.session_state.selected_packages = set()

    # Sidebar for control panels
    with st.sidebar:
        # File Watcher Control Panel
        st.subheader("Automated Ingestion")
        running = is_watcher_running()
        
        status_color = "green" if running else "red"
        status_text = "Running" if running else "Stopped"
        st.markdown(f"Status: **:{status_color}[{status_text}]**")
        
        col1, col2 = st.columns(2)
        if not running:
            if col1.button("Start Watcher", use_container_width=True):
                start_watcher()
                st.rerun()
        else:
            if col1.button("Stop Watcher", use_container_width=True):
                stop_watcher()
                st.rerun()
        
        if col2.button("🔄 Refresh", use_container_width=True):
            st.rerun()

        # Monitoring Stats
        processed_dir = "ingest/processed"
        failed_dir = "ingest/failed"
        
        processed_count = len([f for f in os.listdir(processed_dir)]) if os.path.exists(processed_dir) else 0
        failed_count = len([f for f in os.listdir(failed_dir)]) if os.path.exists(failed_dir) else 0
        
        st.info(f"📁 Processed: {processed_count} | ❌ Failed: {failed_count}")
        st.divider()

        # Cleanup & Archiving
        st.subheader("Cleanup & Archiving")
        show_archived = st.toggle("Show Archived Packages", value=False)
        
        failed_pkgs = get_all_packages(status_filter=["FAILED"], include_archived=False)
        if failed_pkgs:
            if st.button(f"Archive all {len(failed_pkgs)} FAILED", type="secondary", use_container_width=True):
                archive_multiple_packages([p.id for p in failed_pkgs])
                st.success("Archived all failed packages.")
                st.rerun()
        
        if st.session_state.selected_packages:
            if st.button(f"Archive {len(st.session_state.selected_packages)} selected", type="primary", use_container_width=True):
                archive_multiple_packages(list(st.session_state.selected_packages))
                st.session_state.selected_packages = set()
                st.success("Selected packages archived.")
                st.rerun()
        
        st.divider()

        st.subheader("Bulk Actions")
        approved_pkgs = get_all_packages(status_filter=["APPROVED"], include_archived=False)
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
    statuses = ["PENDING", "INGESTING", "INGESTED", "CLASSIFYING", "EXTRACTING", "EXTRACTED", "FAILED", "APPROVED"]
    selected_statuses = st.multiselect("Filter by Status", statuses, default=["INGESTED", "EXTRACTED", "FAILED", "APPROVED"])
    
    # Fetch Data
    packages = get_all_packages(status_filter=selected_statuses, include_archived=show_archived)

    try:
        analytical = AnalyticalService()
        observability_summary = analytical.get_observability_summary()
        recent_failures = analytical.get_recent_failures()
    except Exception as exc:
        observability_summary = pd.DataFrame()
        recent_failures = pd.DataFrame()
        st.warning(f"Observability reporting unavailable: {exc}")

    metrics = build_observability_metrics(observability_summary)
    if metrics:
        st.subheader("Observability Overview")
        metric_columns = st.columns(len(metrics))
        for column, metric in zip(metric_columns, metrics):
            column.metric(metric["label"], metric["value"])

    failure_rows = build_recent_failure_rows(recent_failures)
    if failure_rows:
        st.subheader("Recent Failures")
        st.table(failure_rows)
    
    if not packages:
        st.info("No packages found.")
        return

    # Header Row
    cols = st.columns([0.5, 1, 2, 1.5, 1.5, 1, 1.5])
    cols[0].write("Select")
    cols[1].write("**ID**")
    cols[2].write("**Filename**")
    cols[3].write("**Status**")
    cols[4].write("**Created At**")
    cols[5].write("**Logs**")
    cols[6].write("**Action**")

    # Data Rows
    for pkg in packages:
        with st.container():
            cols = st.columns([0.5, 1, 2, 1.5, 1.5, 1, 1.5])
            
            # Selection Checkbox
            is_selected = pkg.id in st.session_state.selected_packages
            if cols[0].checkbox("Select", value=is_selected, key=f"select_{pkg.id}", label_visibility="collapsed"):
                st.session_state.selected_packages.add(pkg.id)
            else:
                st.session_state.selected_packages.discard(pkg.id)
            
            # Truncate ID for display
            cols[1].write(f"`{pkg.id[:8]}...`")
            cols[2].write(pkg.original_filename)
            
            # Status color coding
            status_map = {
                "FAILED": "red",
                "APPROVED": "green",
                "EXTRACTED": "blue",
                "INGESTED": "orange",
                "PENDING": "gray"
            }
            color = status_map.get(pkg.status, "white")
            archived_suffix = " (Archived)" if pkg.is_archived else ""
            cols[3].markdown(f":{color}[{pkg.status}{archived_suffix}]")
            
            cols[4].write(pkg.created_at.strftime("%Y-%m-%d %H:%M"))
            
            # Log toggle
            show_logs = cols[5].button("📋", key=f"log_btn_{pkg.id}", help="Show Processing Logs")
            
            # Action Buttons
            btn_col1, btn_col2 = cols[6].columns(2)
            if btn_col1.button("Review", key=f"btn_{pkg.id}"):
                st.session_state.current_package_id = pkg.id
                st.session_state.current_view = "Reviewer"
                st.rerun()
            
            if pkg.is_archived:
                if btn_col2.button("♻️", key=f"unarchive_{pkg.id}", help="Unarchive"):
                    archive_package(pkg.id, False)
                    st.rerun()
            else:
                if btn_col2.button("🗑️", key=f"archive_{pkg.id}", help="Archive"):
                    archive_package(pkg.id, True)
                    st.session_state.selected_packages.discard(pkg.id)
                    st.rerun()
                
            if show_logs:
                logs = get_package_logs(pkg.id)
                if logs:
                    with st.expander(f"Processing Logs for {pkg.original_filename}", expanded=True):
                        latest_job = get_latest_extraction_job(pkg.id)
                        log_data = build_log_rows(logs, latest_job=latest_job)
                        st.table(log_data)
                else:
                    st.info("No logs available for this package.")
