import pytest
import os
import sqlite3
import json
import pandas as pd
from src.services.analytical_service import AnalyticalService

@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_packages.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE packages (id TEXT PRIMARY KEY, original_filename TEXT, status TEXT, created_at DATETIME)")
    conn.execute("CREATE TABLE extractions (id INTEGER PRIMARY KEY, package_id TEXT, document_type TEXT, extraction_json TEXT, confidence_score FLOAT, is_reviewed BOOLEAN, created_at DATETIME, FOREIGN KEY(package_id) REFERENCES packages(id))")
    
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
    conn.commit()
    conn.close()
    return str(db_path)

def test_analytical_views(temp_db):
    service = AnalyticalService(db_path=temp_db)
    summary = service.get_summary()
    assert len(summary) == 1
    assert summary.iloc[0]['lender_name'] == "Test Bank"
    assert summary.iloc[0]['filename'] == "test.pdf"
    assert float(summary.iloc[0]['total_amount']) == 1234.56
    
    transactions = service.get_transactions()
    assert len(transactions) == 2
    assert transactions.iloc[0]['component'] == "Principal"
    assert float(transactions.iloc[1]['amount']) == 234.56
