from typing import Any, List, Optional
from pydantic import BaseModel, Field, validator

class BoundingBox(BaseModel):
    """
    Normalized bounding box coordinates [ymin, xmin, ymax, xmax].
    Gemini uses a 0-1000 scale.
    """
    coordinates: List[int] = Field(..., min_items=4, max_items=4)

    @validator("coordinates")
    def validate_coordinates(cls, v):
        if any(c < 0 or c > 1000 for c in v):
            raise ValueError("Coordinates must be between 0 and 1000")
        
        # Allow [0,0,0,0] as it's often returned by models when a field is not found or not groundable
        if all(c == 0 for c in v):
            return v
            
        if v[0] >= v[2] or v[1] >= v[3]:
            raise ValueError(f"Invalid bounding box {v}: ymin must be < ymax and xmin must be < xmax")
        return v

    @property
    def ymin(self) -> int:
        return self.coordinates[0]

    @property
    def xmin(self) -> int:
        return self.coordinates[1]

    @property
    def ymax(self) -> int:
        return self.coordinates[2]

    @property
    def xmax(self) -> int:
        return self.coordinates[3]

class Triplet(BaseModel):
    """
    A field value paired with confidence and visual grounding (bbox).
    """
    value: Any
    confidence: float = Field(..., ge=0.0, le=1.0)
    bbox: Optional[BoundingBox] = None

class ExtractionResult(BaseModel):
    """
    Generic container for extraction results.
    Specific document types will use their own schemas with Triplets.
    """
    document_type: str
    fields: dict[str, Triplet]
    raw_response: Optional[str] = None
