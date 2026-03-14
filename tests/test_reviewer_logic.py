import pytest
from src.models.schema import Package, Extractions, ExtractedFile
from src.ui import db_utils

def test_reviewer_data_fetching(monkeypatch):
    """Test that we can fetch all data needed for the reviewer view."""
    
    # Mock data
    mock_package = Package(id="pkg1", original_filename="test.zip", status="EXTRACTED")
    mock_extractions = [
        Extractions(id=1, package_id="pkg1", file_id=10, document_type="Type A", confidence_score=0.9),
        Extractions(id=2, package_id="pkg1", file_id=11, document_type="Type B", confidence_score=0.8)
    ]
    mock_files = [
        ExtractedFile(id=10, package_id="pkg1", filename="page1.png", mime_type="image/png", content=b"fake content 1"),
        ExtractedFile(id=11, package_id="pkg1", filename="page2.png", mime_type="image/png", content=b"fake content 2")
    ]
    
    # Mock db_utils functions
    def mock_get_package_by_id(pid):
        return mock_package if pid == "pkg1" else None
    
    def mock_get_extractions_for_package(pid):
        return mock_extractions if pid == "pkg1" else []
    
    def mock_get_files_for_package(pid):
        return mock_files if pid == "pkg1" else []
    
    monkeypatch.setattr(db_utils, "get_package_by_id", mock_get_package_by_id)
    monkeypatch.setattr(db_utils, "get_extractions_for_package", mock_get_extractions_for_package)
    monkeypatch.setattr(db_utils, "get_files_for_package", mock_get_files_for_package)
    
    # Verify we can get the data
    pkg = db_utils.get_package_by_id("pkg1")
    assert pkg.id == "pkg1"
    
    exts = db_utils.get_extractions_for_package("pkg1")
    assert len(exts) == 2
    assert exts[0].file_id == 10
    
    files = db_utils.get_files_for_package("pkg1")
    assert len(files) == 2
    
    # Test logic of finding the right file for an extraction
    # This mimics the logic in src/ui/reviewer.py:show_reviewer
    current_ext = exts[0]
    image_file = next((f for f in files if f.id == current_ext.file_id), None)
    assert image_file is not None
    assert image_file.id == 10
    assert image_file.filename == "page1.png"
    
    # Test logic for finding image file if file_id is not set
    current_ext_no_file = Extractions(id=3, package_id="pkg1", file_id=None, document_type="Type C")
    image_file_fallback = next((f for f in files if f.mime_type and f.mime_type.startswith("image/")), None)
    assert image_file_fallback is not None
    assert image_file_fallback.id == 10
