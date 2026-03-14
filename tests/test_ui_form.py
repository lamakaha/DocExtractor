import pytest
import json
from src.ui.reviewer import get_confidence_color
from src.models.triplets import Triplet

def test_get_confidence_color():
    assert get_confidence_color(0.96) == "green"
    assert get_confidence_color(0.95) == "orange"
    assert get_confidence_color(0.70) == "orange"
    assert get_confidence_color(0.69) == "red"
    assert get_confidence_color(0.0) == "red"
    assert get_confidence_color(1.0) == "green"

def test_triplet_parsing():
    extraction_json = {
        "account_number": {
            "value": "123456",
            "confidence": 0.98,
            "bbox": {"coordinates": [100, 100, 200, 200], "label": "account_number"}
        },
        "bank_name": {
            "value": "Test Bank",
            "confidence": 0.50,
            "bbox": None
        }
    }
    
    # Simulating what happens in show_reviewer
    parsed_data = {}
    for field_name, field_triplet in extraction_json.items():
        if isinstance(field_triplet, dict):
            triplet = Triplet(**field_triplet)
        else:
            triplet = field_triplet
        parsed_data[field_name] = triplet
        
    assert isinstance(parsed_data["account_number"], Triplet)
    assert parsed_data["account_number"].value == "123456"
    assert parsed_data["account_number"].confidence == 0.98
    assert parsed_data["account_number"].bbox.coordinates == [100, 100, 200, 200]
    
    assert parsed_data["bank_name"].value == "Test Bank"
    assert parsed_data["bank_name"].confidence == 0.50
    assert parsed_data["bank_name"].bbox is None
