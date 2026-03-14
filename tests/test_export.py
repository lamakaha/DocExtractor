import pytest
import io
import os
from src.services.export_service import ExcelExporter

def test_sanitize_sheet_name():
    exporter = ExcelExporter()
    assert exporter.sanitize_sheet_name("Short Name") == "Short Name"
    assert exporter.sanitize_sheet_name("This is a very long sheet name that exceeds thirty one characters") == "This is a very long sheet name"
    assert exporter.sanitize_sheet_name("Invalid [chars] :*? /\\") == "Invalid chars"

def test_generate_excel():
    exporter = ExcelExporter()
    summary_data = [
        {
            "package_id": "PKG-001",
            "filename": "doc1.pdf",
            "lender_name": "Lender A",
            "document_date": "2023-01-01",
            "total_amount": 1000.50
        },
        {
            "package_id": "PKG-002",
            "filename": "doc2.pdf",
            "lender_name": "Lender B",
            "document_date": "2023-01-02",
            "total_amount": 2500.00
        }
    ]
    
    transactions_data = [
        {"package_id": "PKG-001", "component": "Principal", "amount": 900.00},
        {"package_id": "PKG-001", "component": "Interest", "amount": 100.50},
        {"package_id": "PKG-002", "component": "Principal", "amount": 2500.00}
    ]
    
    output = exporter.generate_excel(summary_data, transactions_data)
    
    assert isinstance(output, io.BytesIO)
    assert output.getbuffer().nbytes > 0
    
    # Optional: Save to file for manual inspection if needed
    # with open("test_output.xlsx", "wb") as f:
    #     f.write(output.getbuffer())

def test_generate_excel_no_transactions():
    exporter = ExcelExporter()
    summary_data = [
        {
            "package_id": "PKG-001",
            "filename": "doc1.pdf",
            "lender_name": "Lender A",
            "document_date": "2023-01-01",
            "total_amount": 1000.50
        }
    ]
    
    output = exporter.generate_excel(summary_data)
    assert isinstance(output, io.BytesIO)
    assert output.getbuffer().nbytes > 0
