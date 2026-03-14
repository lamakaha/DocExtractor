import pytest
from unittest.mock import MagicMock, patch
from src.services.extraction_service import ExtractionService
from src.models.triplets import ExtractionResult, Triplet, BoundingBox

@pytest.fixture(autouse=True)
def mock_env():
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
        yield

@pytest.fixture
def mock_gemini_client():
    with patch("src.services.extraction_service.get_gemini_client") as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client
        yield mock_client

def test_convert_schema_to_json_schema(mock_gemini_client):
    service = ExtractionService()
    extraction_schema = {
        "lender_name": {"description": "Lender Name", "type": "string"},
        "transactions": {
            "description": "List of transactions",
            "type": "list",
            "schema": {
                "amount": "currency"
            }
        }
    }
    json_schema = service._convert_schema_to_json_schema(extraction_schema)
    
    assert json_schema["type"] == "object"
    assert "lender_name" in json_schema["properties"]
    assert "transactions" in json_schema["properties"]
    assert json_schema["properties"]["transactions"]["type"] == "array"
    assert "amount" in json_schema["properties"]["transactions"]["items"]["properties"]

def test_extract_simple_field(mock_gemini_client):
    service = ExtractionService()
    
    # Mock response from OpenAI/OpenRouter
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"lender_name": {"value": "Test Bank", "confidence": 0.99, "bbox": [10, 20, 30, 40]}}'
    mock_gemini_client.chat.completions.create.return_value = mock_response
    
    schema = {"lender_name": {"type": "string"}}
    result = service.extract(b"dummy content", "image/png", "Test_Doc", schema)
    
    assert isinstance(result, ExtractionResult)
    assert result.document_type == "Test_Doc"
    assert "lender_name" in result.fields
    assert result.fields["lender_name"].value == "Test Bank"
    assert result.fields["lender_name"].confidence == 0.99
    assert result.fields["lender_name"].bbox.coordinates == [10, 20, 30, 40]

def test_extract_list_field(mock_gemini_client):
    service = ExtractionService()
    
    # Mock response from OpenAI/OpenRouter with list of items
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = """
    {
        "transactions": [
            {
                "amount": {"value": "100.00", "confidence": 0.9, "bbox": [100, 100, 110, 200]}
            },
            {
                "amount": {"value": "200.00", "confidence": 0.8, "bbox": [200, 100, 210, 200]}
            }
        ]
    }
    """
    mock_gemini_client.chat.completions.create.return_value = mock_response
    
    schema = {
        "transactions": {
            "type": "list",
            "schema": {"amount": "currency"}
        }
    }
    result = service.extract(b"dummy content", "image/png", "Test_Doc", schema)
    
    assert "transactions" in result.fields
    transactions_triplet = result.fields["transactions"]
    assert isinstance(transactions_triplet, Triplet)
    assert isinstance(transactions_triplet.value, list)
    assert len(transactions_triplet.value) == 2
    
    first_item = transactions_triplet.value[0]
    assert "amount" in first_item
    assert isinstance(first_item["amount"], Triplet)
    assert first_item["amount"].value == "100.00"

def test_to_triplet_recursive(mock_gemini_client):
    service = ExtractionService()
    
    raw_data = {
        "value": [
            {
                "subfield": {"value": "subval", "confidence": 0.5, "bbox": [1, 2, 3, 4]}
            }
        ],
        "confidence": 1.0,
        "bbox": [0, 0, 10, 10]
    }
    
    triplet = service._to_triplet(raw_data)
    assert isinstance(triplet, Triplet)
    assert isinstance(triplet.value, list)
    assert isinstance(triplet.value[0]["subfield"], Triplet)
    assert triplet.value[0]["subfield"].value == "subval"
