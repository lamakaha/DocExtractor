import os
import json
import base64
import time
from typing import Dict, Any, List, Optional
from src.services.gemini_client import get_gemini_client
from src.models.triplets import Triplet, ExtractionResult, BoundingBox

class ExtractionService:
    """
    Service for structured document extraction using OpenRouter (Gemini 2.0 Flash).
    Returns results as Triplets (Value, Confidence, BBox).
    """

    def __init__(self):
        self._client = None
        self.model_id = os.getenv("GEMINI_MODEL", "google/gemini-2.0-flash-001")
        self.prompt_version = "extraction.v1.structured-json"
        self.last_run_details: Dict[str, Any] = {}

    @property
    def client(self):
        if self._client is None:
            self._client = get_gemini_client()
        return self._client

    def _convert_schema_to_json_schema(self, extraction_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Converts a configuration extraction schema into a standard JSON schema.
        Each field is expected to be returned as a Triplet structure.
        """
        properties = {}
        required = []

        triplet_schema = {
            "type": "object",
            "properties": {
                "value": {"type": "string", "description": "The extracted value (string, number, or date)."},
                "confidence": {"type": "number", "description": "Confidence score 0-1.0."},
                "bbox": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Normalized bounding box [ymin, xmin, ymax, xmax] (0-1000).",
                    "minItems": 4,
                    "maxItems": 4
                }
            },
            "required": ["value", "confidence", "bbox"]
        }

        for field_name, field_def in extraction_schema.items():
            field_type = field_def.get("type", "string")
            description = field_def.get("description", "")

            if field_type == "list":
                item_schema = field_def.get("schema", {})
                item_properties = {}
                item_required = []
                for sub_field, sub_type in item_schema.items():
                    # For list items, each property is also a triplet
                    item_properties[sub_field] = triplet_schema
                    item_required.append(sub_field)
                
                properties[field_name] = {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": item_properties,
                        "required": item_required
                    },
                    "description": description
                }
            else:
                # Standard field is a triplet
                properties[field_name] = triplet_schema
            
            required.append(field_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required
        }

    def _to_triplet(self, data: Any, wrap_as_field: bool = False) -> Any:
        """
        Recursively converts raw JSON extraction into Triplet objects.
        """
        if isinstance(data, dict):
            if "value" in data and "confidence" in data:
                # This looks like a triplet-like structure from LLM
                bbox_raw = data.get("bbox")
                bbox = BoundingBox(coordinates=bbox_raw) if bbox_raw else None
                
                # Check if value itself is a list or dict that needs conversion
                val = data.get("value")
                if isinstance(val, (dict, list)):
                    val = self._to_triplet(val)
                
                return Triplet(
                    value=val,
                    confidence=data.get("confidence", 0.0),
                    bbox=bbox
                )
            else:
                # Generic dictionary, convert its values
                return {k: self._to_triplet(v) for k, v in data.items()}
        elif isinstance(data, list):
            # List of items, convert each item
            items = [self._to_triplet(item) for item in data]
            if wrap_as_field:
                # If this list is a top-level field, it must be wrapped in a Triplet
                return Triplet(value=items, confidence=1.0)
            return items
        return data

    def extract(self, content: bytes, mime_type: str, doc_type: str, extraction_schema: Dict[str, Any]) -> ExtractionResult:
        """
        Extracts structured data from a document package using OpenRouter.
        """
        json_schema = self._convert_schema_to_json_schema(extraction_schema)

        prompt = f"""Extract data from this '{doc_type}' document as structured JSON.
For every field, provide:
1. 'value': The normalized value (e.g. 15000.00 for currency, YYYY-MM-DD for dates).
2. 'confidence': Your confidence in this extraction (0.0 to 1.0).
3. 'bbox': The bounding box coordinates [ymin, xmin, ymax, xmax] in 0-1000 scale.

IMPORTANT: Ensure the bounding boxes are accurate for each specific value extracted.
If a field is not found, use null for value and 0.0 for confidence.
"""

        try:
            start = time.perf_counter()
            # Prepare content for OpenRouter (OpenAI-compatible)
            base64_content = base64.b64encode(content).decode("utf-8")

            # We use response_format if supported, or just ask for JSON in prompt
            # Many models support JSON mode through response_format
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_content}"
                                }
                            }
                        ]
                    }
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "document_extraction",
                        "strict": False,
                        "schema": json_schema
                    }
                },
                temperature=0.0
            )

            raw_data = response.choices[0].message.content
            extracted_fields_json = json.loads(raw_data)
            usage = getattr(response, "usage", None)
            self.last_run_details = {
                "model_id": self.model_id,
                "prompt_version": self.prompt_version,
                "document_type": doc_type,
                "schema_field_count": len(extraction_schema),
                "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                "usage": {
                    "prompt_tokens": getattr(usage, "prompt_tokens", None),
                    "completion_tokens": getattr(usage, "completion_tokens", None),
                    "total_tokens": getattr(usage, "total_tokens", None),
                } if usage else None,
            }
            
            # Convert JSON to Triplet objects and validate
            processed_fields = {}
            for field_name, field_val in extracted_fields_json.items():
                processed_fields[field_name] = self._to_triplet(field_val, wrap_as_field=True)

            return ExtractionResult(
                document_type=doc_type,
                fields=processed_fields,
                raw_response=raw_data
            )

        except Exception as e:
            self.last_run_details = {
                "model_id": self.model_id,
                "prompt_version": self.prompt_version,
                "document_type": doc_type,
                "schema_field_count": len(extraction_schema),
                "error": str(e),
            }
            print(f"Extraction failed: {e}")
            raise
