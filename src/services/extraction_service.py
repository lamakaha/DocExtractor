import json
from typing import Dict, Any, List, Optional
from google.genai import types
from pydantic import BaseModel, create_model, Field
from src.services.gemini_client import get_gemini_client
from src.models.triplets import Triplet, ExtractionResult, BoundingBox

class ExtractionService:
    """
    Service for structured document extraction using Gemini 1.5 Pro.
    Returns results as Triplets (Value, Confidence, BBox).
    """

    def __init__(self):
        self.client = get_gemini_client()
        self.model_id = "gemini-1.5-pro"

    def _convert_schema_to_gemini(self, extraction_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Converts a configuration extraction schema into a Gemini-compatible JSON schema.
        Each field is expected to be returned as a Triplet structure.
        """
        properties = {}
        required = []

        triplet_schema = {
            "type": "OBJECT",
            "properties": {
                "value": {"type": "STRING", "description": "The extracted value (string, number, or date)."},
                "confidence": {"type": "NUMBER", "description": "Confidence score 0-1.0."},
                "bbox": {
                    "type": "ARRAY",
                    "items": {"type": "INTEGER"},
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
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
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
            "type": "OBJECT",
            "properties": properties,
            "required": required
        }

    def _to_triplet(self, data: Any, wrap_as_field: bool = False) -> Any:
        """
        Recursively converts raw JSON extraction into Triplet objects.
        """
        if isinstance(data, dict):
            if "value" in data and "confidence" in data and ("bbox" in data or "bbox" not in data):
                # This looks like a triplet-like structure from Gemini
                # Note: 'bbox' might be missing if field not found, though schema requires it
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
        Extracts structured data from a document package using Gemini 1.5 Pro.
        """
        gemini_schema = self._convert_schema_to_gemini(extraction_schema)

        prompt = f"""Extract data from this '{doc_type}' document as structured JSON.
For every field, provide:
1. 'value': The normalized value (e.g. 15000.00 for currency, YYYY-MM-DD for dates).
2. 'confidence': Your confidence in this extraction (0.0 to 1.0).
3. 'bbox': The bounding box coordinates [ymin, xmin, ymax, xmax] in 0-1000 scale.

IMPORTANT: Ensure the bounding boxes are accurate for each specific value extracted.
If a field is not found, use null for value and 0.0 for confidence.
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
                    response_mime_type="application/json",
                    response_schema=gemini_schema,
                    temperature=0.0
                )
            )

            raw_data = response.text
            extracted_fields_json = json.loads(raw_data)
            
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
            print(f"Extraction failed: {e}")
            raise
