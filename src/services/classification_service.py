import os
import json
import glob
import base64
import time
from typing import List, Dict, Optional, Any
from src.services.gemini_client import get_gemini_client

class ClassificationService:
    """
    Service for document classification using OpenRouter (Gemini 2.0 Flash).
    Uses 'classification_cues' from configurations to identify document types.
    """

    def __init__(self, configs_path: str = "configs"):
        self.configs_path = configs_path
        self._client = None
        self.model_id = os.getenv("GEMINI_MODEL", "google/gemini-2.0-flash-001")
        self.prompt_version = "classification.v2.package-context"
        self._doc_type_cues: Dict[str, List[str]] = self._load_cues()
        self.last_run_details: Dict[str, Any] = {}

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

    def classify(
        self,
        content: bytes | List[bytes],
        mime_type: str | List[str],
        text_context: str = "",
    ) -> str:
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

        context_note = ""
        if text_context.strip():
            context_note = f"""

Additional package text context:
{text_context.strip()}
"""

        prompt = f"""You are a document classifier. Identify the document type from the following list based on the visual and textual content across the provided package context:

{cues_description}
{context_note}

If the document does not match any of the above, return 'UNKNOWN'.
Return ONLY the document type name as a string (e.g., 'Commercial_Loan_Paydown' or 'UNKNOWN').
"""

        try:
            start = time.perf_counter()
            contents = content if isinstance(content, list) else [content]
            mime_types = mime_type if isinstance(mime_type, list) else [mime_type]
            content_parts = [{"type": "text", "text": prompt}]
            for idx, item in enumerate(contents):
                current_mime = mime_types[idx] if idx < len(mime_types) else mime_types[0]
                base64_content = base64.b64encode(item).decode("utf-8")
                content_parts.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{current_mime};base64,{base64_content}"
                        }
                    }
                )

            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {
                        "role": "user",
                        "content": content_parts
                    }
                ],
                temperature=0.0
            )

            result = response.choices[0].message.content.strip()
            usage = getattr(response, "usage", None)
            self.last_run_details = {
                "model_id": self.model_id,
                "prompt_version": self.prompt_version,
                "content_items": len(contents),
                "text_context_chars": len(text_context),
                "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                "usage": {
                    "prompt_tokens": getattr(usage, "prompt_tokens", None),
                    "completion_tokens": getattr(usage, "completion_tokens", None),
                    "total_tokens": getattr(usage, "total_tokens", None),
                } if usage else None,
            }
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
            self.last_run_details = {
                "model_id": self.model_id,
                "prompt_version": self.prompt_version,
                "error": str(e),
            }
            print(f"Classification failed: {e}")
            return "UNKNOWN"

    def get_supported_types(self) -> List[str]:
        return list(self._doc_type_cues.keys())
