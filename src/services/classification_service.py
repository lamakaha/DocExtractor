import os
import json
import glob
from typing import List, Dict, Optional, Any
from google.genai import types
from src.services.gemini_client import get_gemini_client

class ClassificationService:
    """
    Service for document classification using Gemini 1.5 Pro.
    Uses 'classification_cues' from configurations to identify document types.
    """

    def __init__(self, configs_path: str = "configs"):
        self.configs_path = configs_path
        self._client = None
        self.model_id = "gemini-1.5-pro"
        self._doc_type_cues: Dict[str, List[str]] = self._load_cues()

    @property
    def client(self):
        if self._client is None:
            self._client = get_gemini_client()
        return self._client

    def _load_cues(self) -> Dict[str, List[str]]:
        """
        Loads all classification cues from the configs directory.
        Returns a mapping from document_type to its list of cues.
        """
        cues_map = {}
        config_files = glob.glob(os.path.join(self.configs_path, "*.json"))
        for config_file in config_files:
            try:
                with open(config_file, "r") as f:
                    config = json.load(f)
                    doc_type = config.get("document_type")
                    cues = config.get("classification_cues")
                    if doc_type and cues:
                        cues_map[doc_type] = cues
            except (json.JSONDecodeError, OSError) as e:
                print(f"Error loading config {config_file}: {e}")
        return cues_map

    def classify(self, content: bytes, mime_type: str) -> str:
        """
        Classifies the document into one of the known document types.
        If no match is found with high confidence, returns 'UNKNOWN'.
        """
        if not self._doc_type_cues:
            return "UNKNOWN"

        # Construct prompt based on cues
        cues_description = "\n".join([
            f"- {doc_type}: Matches if document contains: {', '.join(cues)}"
            for doc_type, cues in self._doc_type_cues.items()
        ])

        prompt = f"""You are a document classifier. Identify the document type from the following list based on the visual and textual content:

{cues_description}

If the document does not match any of the above, return 'UNKNOWN'.
Return ONLY the document type name as a string (e.g., 'Commercial_Loan_Paydown' or 'UNKNOWN').
"""

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_bytes(data=content, mime_type=mime_type),
                            types.Part.from_text(text=prompt)
                        ]
                    )
                ],
                config=types.GenerateContentConfig(
                    temperature=0.0
                )
            )
            
            result = response.text.strip()
            # Basic validation that result is in our map or UNKNOWN
            if result in self._doc_type_cues or result == "UNKNOWN":
                return result
            else:
                # If LLM returned something weird, default to UNKNOWN or find closest
                for doc_type in self._doc_type_cues:
                    if doc_type.lower() in result.lower():
                        return doc_type
                return "UNKNOWN"
                
        except Exception as e:
            print(f"Classification failed: {e}")
            return "UNKNOWN"

    def get_supported_types(self) -> List[str]:
        return list(self._doc_type_cues.keys())
