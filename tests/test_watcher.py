import os
import time
import shutil
import pytest
from unittest.mock import MagicMock, patch
from src.services.watcher import IngestionHandler

@pytest.fixture
def handler_setup(tmp_path):
    ingest_dir = tmp_path / "ingest"
    processed_dir = ingest_dir / "processed"
    failed_dir = ingest_dir / "failed"
    
    os.makedirs(processed_dir)
    os.makedirs(failed_dir)
    
    # Patch the services to avoid initialization issues (like missing API keys)
    with patch('src.services.watcher.RecursiveIngestor') as mock_ingestor_cls, \
         patch('src.services.watcher.ExtractionPipeline') as mock_pipeline_cls:
        
        handler = IngestionHandler(str(processed_dir), str(failed_dir))
        
        # Access the instances created during init
        handler.ingestor = mock_ingestor_cls.return_value
        handler.pipeline = mock_pipeline_cls.return_value
        
        yield handler, ingest_dir, processed_dir, failed_dir

def test_handler_processes_file(handler_setup):
    handler, ingest_dir, processed_dir, failed_dir = handler_setup
    
    # Create a dummy zip file
    test_file = ingest_dir / "test.zip"
    test_file.write_bytes(b"dummy zip content")
    
    # Configure mock
    handler.ingestor.process_package.return_value = "pkg_123"
    
    # Trigger event
    handler._process_new_file(str(test_file))
    
    # Verify service calls
    handler.ingestor.process_package.assert_called_once()
    handler.pipeline.process_package.assert_called_once_with("pkg_123")
    
    # Verify file moved to processed
    assert not test_file.exists()
    assert (processed_dir / "test.zip").exists()

def test_handler_ignores_unsupported_extension(handler_setup):
    handler, ingest_dir, processed_dir, failed_dir = handler_setup
    
    test_file = ingest_dir / "test.txt"
    test_file.write_text("not supported")
    
    handler._process_new_file(str(test_file))
    
    handler.ingestor.process_package.assert_not_called()
    assert test_file.exists()

def test_handler_moves_to_failed_on_error(handler_setup):
    handler, ingest_dir, processed_dir, failed_dir = handler_setup
    
    test_file = ingest_dir / "error.pdf"
    test_file.write_bytes(b"dummy pdf")
    
    # Force error
    handler.ingestor.process_package.side_effect = Exception("Ingestion failed")
    
    handler._process_new_file(str(test_file))
    
    assert not test_file.exists()
    assert (failed_dir / "error.pdf").exists()
