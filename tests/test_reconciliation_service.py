from src.services.reconciliation_service import ReconciliationService


def test_reconcile_prefers_higher_confidence_value():
    service = ReconciliationService()

    result = service.reconcile(
        [
            {"lender_name": {"value": "Bank A", "confidence": 0.7, "bbox": {"coordinates": [1, 1, 2, 2]}, "page_number": 1}},
            {"lender_name": {"value": "Bank B", "confidence": 0.9, "bbox": {"coordinates": [3, 3, 4, 4]}, "page_number": 2}},
        ]
    )

    assert result["lender_name"]["value"] == "Bank B"
    assert result["lender_name"]["page_number"] == 2


def test_reconcile_fills_missing_value_from_later_page():
    service = ReconciliationService()

    result = service.reconcile(
        [
            {"account_number": {"value": "", "confidence": 0.8, "bbox": None, "page_number": 1}},
            {"account_number": {"value": "12345", "confidence": 0.6, "bbox": {"coordinates": [5, 5, 6, 6]}, "page_number": 2}},
        ]
    )

    assert result["account_number"]["value"] == "12345"
    assert result["account_number"]["page_number"] == 2


def test_reconcile_merges_list_values():
    service = ReconciliationService()

    result = service.reconcile(
        [
            {"transactions": {"value": [{"id": 1}], "confidence": 0.7, "bbox": {"coordinates": [1, 1, 2, 2]}, "page_number": 1}},
            {"transactions": {"value": [{"id": 2}], "confidence": 0.8, "bbox": {"coordinates": [3, 3, 4, 4]}, "page_number": 2}},
        ]
    )

    assert result["transactions"]["value"] == [{"id": 1}, {"id": 2}]
    assert result["transactions"]["page_number"] == 2
