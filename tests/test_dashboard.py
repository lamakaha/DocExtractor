import pandas as pd
from datetime import datetime

from src.models.schema import ExtractionJob, PackageLog
from src.ui.dashboard import build_log_rows, build_observability_metrics, build_recent_failure_rows


def test_build_log_rows_includes_metadata_and_diagnostics():
    logs = [
        PackageLog(
            package_id="pkg1",
            timestamp=datetime.utcnow(),
            stage="CLASSIFICATION",
            level="SUCCESS",
            message="classified",
            details='{"model_id":"m1","prompt_version":"p1","latency_ms":15.5,"usage":{"total_tokens":42},"content_items":2}',
        ),
        PackageLog(
            package_id="pkg1",
            timestamp=datetime.utcnow(),
            stage="QUEUE",
            level="ERROR",
            message="failed",
            details='{"last_error":"boom"}',
        ),
    ]
    job = ExtractionJob(package_id="pkg1", job_type="EXTRACT_PACKAGE", status="FAILED", attempts=3, max_attempts=3, last_error="boom")

    rows = build_log_rows(logs, latest_job=job)

    assert "model=m1" in rows[0]["Metadata"]
    assert "prompt=p1" in rows[0]["Metadata"]
    assert "tokens=42" in rows[0]["Metadata"]
    assert "job=FAILED 3/3" in rows[1]["Diagnostics"]
    assert "job_error=boom" in rows[1]["Diagnostics"]


def test_build_observability_metrics_formats_summary_values():
    summary_df = pd.DataFrame(
        [
            {
                "error_logs": 2,
                "retrying_jobs": 1,
                "avg_latency_ms": 18.48,
                "avg_total_tokens": 101.0,
            }
        ]
    )

    metrics = build_observability_metrics(summary_df)

    assert metrics[0] == {"label": "Errors", "value": 2}
    assert metrics[1] == {"label": "Retries", "value": 1}
    assert metrics[2] == {"label": "Avg Latency", "value": "18.5ms"}
    assert metrics[3] == {"label": "Avg Tokens", "value": "101"}


def test_build_recent_failure_rows_formats_retry_and_error_columns():
    failures_df = pd.DataFrame(
        [
            {
                "timestamp": datetime(2026, 3, 16, 9, 30),
                "package_id": "pkg123456789",
                "stage": "EXTRACTION",
                "level": "ERROR",
                "message": "failed extraction",
                "job_status": "FAILED",
                "attempts": 3,
                "max_attempts": 3,
                "last_error": "boom",
            }
        ]
    )

    rows = build_recent_failure_rows(failures_df)

    assert rows[0]["Package"] == "pkg12345"
    assert rows[0]["Attempts"] == "3/3"
    assert rows[0]["Job"] == "FAILED"
    assert rows[0]["Error"] == "boom"
