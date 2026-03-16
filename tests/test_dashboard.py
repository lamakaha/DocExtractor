from datetime import datetime

from src.models.schema import ExtractionJob, PackageLog
from src.ui.dashboard import build_log_rows


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
