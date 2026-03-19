import pytest
import json
from src.ui.reviewer import serialize_triplet
from src.models.triplets import Triplet, BoundingBox

def test_serialize_triplet():
    bbox = BoundingBox(coordinates=[1, 2, 3, 4])
    triplet = Triplet(value="val", confidence=0.9, bbox=bbox)
    
    # Test individual serialization
    assert serialize_triplet(bbox) == {"coordinates": [1, 2, 3, 4]}
    assert serialize_triplet(triplet) == {
        "value": "val", 
        "confidence": 0.9, 
        "bbox": {"coordinates": [1, 2, 3, 4]},
        "page_number": None
    }
    
    with pytest.raises(TypeError):
        serialize_triplet("not a triplet")

def test_json_reconstruction():
    extraction_data = {
        "field1": Triplet(value="old_val", confidence=0.9, bbox=None)
    }
    new_values = {"field1": "new_val"}
    
    # Simulating what happens in show_reviewer
    updated_data = extraction_data.copy()
    for field_name, new_val in new_values.items():
        if isinstance(updated_data[field_name], dict):
            updated_data[field_name]['value'] = new_val
        else:
            updated_data[field_name].value = new_val
            
    # Re-serialization
    reconstructed_json = json.loads(json.dumps(updated_data, default=serialize_triplet))
    
    assert reconstructed_json["field1"]["value"] == "new_val"
    assert reconstructed_json["field1"]["confidence"] == 0.9
    assert reconstructed_json["field1"]["bbox"] is None
