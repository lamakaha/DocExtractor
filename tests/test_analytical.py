import pytest
import sqlite3
import json
import uuid
from pathlib import Path
from src.services.analytical_service import AnalyticalService

@pytest.fixture
def temp_db():
    base_dir = Path.cwd() / ".tmp-analytical-tests"
    base_dir.mkdir(exist_ok=True)
    db_path = base_dir / f"test_packages_{uuid.uuid4().hex}.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE packages (id TEXT PRIMARY KEY, original_filename TEXT, status TEXT, created_at DATETIME)")
    conn.execute("CREATE TABLE extractions (id INTEGER PRIMARY KEY, package_id TEXT, document_type TEXT, extraction_json TEXT, confidence_score FLOAT, is_reviewed BOOLEAN, created_at DATETIME, FOREIGN KEY(package_id) REFERENCES packages(id))")
    conn.execute("CREATE TABLE package_logs (id INTEGER PRIMARY KEY, package_id TEXT, timestamp DATETIME, level TEXT, stage TEXT, message TEXT, details TEXT)")
    conn.execute("CREATE TABLE extraction_jobs (id INTEGER PRIMARY KEY, package_id TEXT, job_type TEXT, status TEXT, attempts INTEGER, max_attempts INTEGER, last_error TEXT, created_at DATETIME, updated_at DATETIME)")
    
    sample_data = {
        "lender_name": {"value": "Test Bank", "confidence": 0.9},
        "total_amount": {"value": "1234.56", "confidence": 0.95},
        "effective_date": {"value": "2023-01-01", "confidence": 0.9},
        "transactions": {
            "value": [
                {"component": {"value": "Principal"}, "amount": {"value": "1000.00"}},
                {"component": {"value": "Interest"}, "amount": {"value": "234.56"}}
            ],
            "confidence": 1.0
        }
    }
    
    conn.execute("INSERT INTO packages VALUES (?, ?, ?, ?)", ("pkg1", "test.pdf", "APPROVED", "2023-01-01"))
    conn.execute("INSERT INTO extractions (package_id, document_type, extraction_json, confidence_score, is_reviewed, created_at) VALUES (?, ?, ?, ?, ?, ?)", 
                 ("pkg1", "Bank Paydown", json.dumps(sample_data), 0.92, True, "2023-01-01"))
    conn.execute(
        "INSERT INTO package_logs (package_id, timestamp, level, stage, message, details) VALUES (?, ?, ?, ?, ?, ?)",
        ("pkg1", "2023-01-01 10:00:00", "SUCCESS", "CLASSIFICATION", "classified", '{"model_id":"m1","latency_ms":12.5,"usage":{"total_tokens":80}}'),
    )
    conn.execute(
        "INSERT INTO package_logs (package_id, timestamp, level, stage, message, details) VALUES (?, ?, ?, ?, ?, ?)",
        ("pkg1", "2023-01-01 10:01:00", "ERROR", "EXTRACTION", "failed extraction", '{"last_error":"rate limited","latency_ms":24.5,"usage":{"total_tokens":120}}'),
    )
    conn.execute(
        "INSERT INTO extraction_jobs (package_id, job_type, status, attempts, max_attempts, last_error, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("pkg1", "EXTRACT_PACKAGE", "FAILED", 3, 3, "rate limited", "2023-01-01 10:00:00", "2023-01-01 10:02:00"),
    )
    conn.commit()
    conn.close()
    return str(db_path)

@pytest.fixture
def temp_configs():
    base_dir = Path.cwd() / ".tmp-analytical-tests"
    base_dir.mkdir(exist_ok=True)
    config_dir = base_dir / f"configs_{uuid.uuid4().hex}"
    config_dir.mkdir()
    bank_paydown = {
        "document_type": "Bank Paydown",
        "analytical_mappings": {
            "summary": {
                "lender_name": {"path": "$.lender_name.value", "type": "string"},
                "total_amount": {"path": "$.total_amount.value", "type": "decimal"},
                "document_date": {"path": "$.effective_date.value", "type": "string"},
            },
            "transactions": {
                "path": "$.transactions.value",
                "fields": {
                    "component": {"path": "$.component.value", "type": "string"},
                    "amount": {"path": "$.amount.value", "type": "decimal"},
                },
            },
        },
    }
    secondary_doc = {
        "document_type": "Fee Notice",
        "analytical_mappings": {
            "summary": {
                "lender_name": {"path": "$.issuer.value", "type": "string"},
                "total_amount": {"path": "$.fee_total.value", "type": "decimal"},
                "document_date": {"path": "$.notice_date.value", "type": "string"},
            }
        },
    }
    (config_dir / "bank_paydown.json").write_text(json.dumps(bank_paydown), encoding="utf-8")
    (config_dir / "fee_notice.json").write_text(json.dumps(secondary_doc), encoding="utf-8")
    return str(config_dir)

def test_analytical_views(temp_db, temp_configs):
    service = AnalyticalService(db_path=temp_db, configs_path=temp_configs)
    summary = service.get_summary()
    assert len(summary) == 1
    assert summary.iloc[0]['lender_name'] == "Test Bank"
    assert summary.iloc[0]['filename'] == "test.pdf"
    assert float(summary.iloc[0]['total_amount']) == 1234.56
    assert summary.iloc[0]['document_date'] == "2023-01-01"
    
    transactions = service.get_transactions()
    assert len(transactions) == 2
    assert transactions.iloc[0]['component'] == "Principal"
    assert float(transactions.iloc[1]['amount']) == 234.56


def test_analytical_views_skip_unconfigured_transaction_docs(temp_configs):
    base_dir = Path.cwd() / ".tmp-analytical-tests"
    base_dir.mkdir(exist_ok=True)
    db_path = base_dir / f"test_packages_{uuid.uuid4().hex}.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE packages (id TEXT PRIMARY KEY, original_filename TEXT, status TEXT, created_at DATETIME)")
    conn.execute("CREATE TABLE extractions (id INTEGER PRIMARY KEY, package_id TEXT, document_type TEXT, extraction_json TEXT, confidence_score FLOAT, is_reviewed BOOLEAN, created_at DATETIME, FOREIGN KEY(package_id) REFERENCES packages(id))")
    conn.execute("INSERT INTO packages VALUES (?, ?, ?, ?)", ("pkg2", "fee.pdf", "APPROVED", "2023-01-01"))
    conn.execute(
        "INSERT INTO extractions (package_id, document_type, extraction_json, confidence_score, is_reviewed, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("pkg2", "Fee Notice", json.dumps({"issuer": {"value": "Issuer A"}, "fee_total": {"value": "99.50"}, "notice_date": {"value": "2024-01-01"}}), 0.9, True, "2023-01-01")
    )
    conn.commit()
    conn.close()

    service = AnalyticalService(db_path=str(db_path), configs_path=temp_configs)
    summary = service.get_summary()
    assert len(summary) == 1
    assert summary.iloc[0]["lender_name"] == "Issuer A"
    transactions = service.get_transactions()
    assert transactions.empty


def test_observability_summary_and_recent_failures(temp_db, temp_configs):
    service = AnalyticalService(db_path=temp_db, configs_path=temp_configs)

    summary = service.get_observability_summary()
    assert len(summary) == 1
    assert int(summary.iloc[0]["total_logs"]) == 2
    assert int(summary.iloc[0]["error_logs"]) == 1
    assert int(summary.iloc[0]["failed_jobs"]) == 1
    assert summary.iloc[0]["avg_latency_ms"] == pytest.approx(18.5)
    assert summary.iloc[0]["avg_total_tokens"] == pytest.approx(100.0)
    assert int(summary.iloc[0]["classification_runs"]) == 1
    assert int(summary.iloc[0]["extraction_runs"]) == 1

    failures = service.get_recent_failures(limit=5)
    assert len(failures) == 1
    assert failures.iloc[0]["package_id"] == "pkg1"
    assert failures.iloc[0]["job_status"] == "FAILED"
    assert failures.iloc[0]["last_error"] == "rate limited"
