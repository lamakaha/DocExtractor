from src.services.extraction_service import ExtractionService


def test_build_prompt_requests_tight_value_only_bboxes():
    service = ExtractionService()

    prompt = service._build_prompt("Commercial_Loan_Paydown")

    assert "tightly cover only the exact printed value" in prompt
    assert "return bbox as [0, 0, 0, 0]" in prompt
    assert "Do not guess a bbox from layout alone" in prompt


def test_build_bbox_audit_flags_suspicious_patterns():
    service = ExtractionService()

    audit = service._build_bbox_audit(
        {
            "lender_name": {"value": "North River Bank", "confidence": 0.99, "bbox": [90, 49, 96, 120]},
            "effective_date": {"value": "2026-03-31", "confidence": 0.99, "bbox": [90, 49, 96, 120]},
            "total_amount": {"value": "15250.45", "confidence": 0.98, "bbox": [115, 106, 122, 165]},
            "reference": {"value": "NRB-445821", "confidence": 0.92, "bbox": [0, 0, 0, 0]},
        }
    )

    assert audit["suspicious_field_count"] >= 2
    assert "duplicate_bbox" in audit["flagged_fields"]["lender_name"]
    assert "duplicate_bbox" in audit["flagged_fields"]["effective_date"]
    assert "ungrounded_bbox_zeroed" in audit["flagged_fields"]["reference"]
