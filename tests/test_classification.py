import pytest
from unittest.mock import MagicMock, patch
from src.services.classification_service import ClassificationService

@pytest.fixture(autouse=True)
def mock_env():
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
        yield

@pytest.fixture
def mock_gemini_client():
    with patch("src.services.classification_service.get_gemini_client") as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client
        yield mock_client

def test_load_cues():
    with patch("glob.glob") as mock_glob, \
         patch("builtins.open", MagicMock()) as mock_open, \
         patch("json.load") as mock_json_load:
        
        mock_glob.return_value = ["configs/test.json"]
        mock_json_load.return_value = {
            "document_type": "TestType",
            "classification_cues": ["Cue1", "Cue2"]
        }
        
        service = ClassificationService()
        assert "TestType" in service._doc_type_cues
        assert service._doc_type_cues["TestType"] == ["Cue1", "Cue2"]

def test_classify(mock_gemini_client):
    with patch.object(ClassificationService, "_load_cues") as mock_load:
        mock_load.return_value = {"Commercial_Loan_Paydown": ["cue1"]}
        service = ClassificationService()
        
        # Mock response from OpenAI/OpenRouter
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Commercial_Loan_Paydown"
        mock_gemini_client.chat.completions.create.return_value = mock_response
        
        result = service.classify(b"dummy", "application/pdf")
        assert result == "Commercial_Loan_Paydown"
        assert service.last_run_details["content_items"] == 1
        assert service.last_run_details["model_id"] == service.model_id

def test_classify_unknown(mock_gemini_client):
    with patch.object(ClassificationService, "_load_cues") as mock_load:
        mock_load.return_value = {"TypeA": ["cue1"]}
        service = ClassificationService()
        
        # Mock response from OpenAI/OpenRouter
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Something else entirely"
        mock_gemini_client.chat.completions.create.return_value = mock_response
        
        result = service.classify(b"dummy", "application/pdf")
        assert result == "UNKNOWN"


def test_classify_with_package_context(mock_gemini_client):
    with patch.object(ClassificationService, "_load_cues") as mock_load:
        mock_load.return_value = {"Commercial_Loan_Paydown": ["cue1"]}
        service = ClassificationService()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Commercial_Loan_Paydown"
        mock_gemini_client.chat.completions.create.return_value = mock_response

        result = service.classify(
            [b"page1", b"page2"],
            ["image/png", "image/png"],
            text_context="body text context",
        )

        assert result == "Commercial_Loan_Paydown"
        call_kwargs = mock_gemini_client.chat.completions.create.call_args.kwargs
        content_parts = call_kwargs["messages"][0]["content"]
        assert len(content_parts) == 3
        assert "body text context" in content_parts[0]["text"]
        assert service.last_run_details["content_items"] == 2
        assert service.last_run_details["text_context_chars"] == len("body text context")
