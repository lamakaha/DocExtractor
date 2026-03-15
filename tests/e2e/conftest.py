import os
import sys
import time
import subprocess
import pytest
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models.schema import Base, Package, Extractions, ExtractedFile

@pytest.fixture(scope="session", autouse=True)
def start_streamlit():
    """
    Spawns the Streamlit app before E2E tests run.
    Ensures test data isolation and dummy API keys are used.
    """
    env = os.environ.copy()
    env["DATABASE_URL"] = "sqlite:///test_e2e.db"
    env["OPENROUTER_API_KEY"] = "dummy"

    # Start the Streamlit application
    # using sys.executable -m streamlit to ensure we use the correct python environment
    process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "src/ui/app.py", "--server.port=8502", "--server.headless=true"],
        env=env
    )
    
    # Wait for the server to spin up
    time.sleep(5)
    
    yield
    
    # Terminate the server after tests complete
    process.terminate()
    process.wait()

@pytest.fixture(scope="function")
def seed_db():
    engine = create_engine("sqlite:///test_e2e.db")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    pkg1 = Package(id="pkg_test_ingested", original_filename="ingested_doc.zip", status="INGESTED")
    pkg2 = Package(id="pkg_test_approved", original_filename="approved_doc.zip", status="APPROVED")
    
    dummy_extraction_json = json.dumps({
        "lender_name": {"value": "Test Bank", "confidence": 0.9},
        "total_amount": {"value": 1000.50, "confidence": 0.8},
        "effective_date": {"value": "2023-01-01", "confidence": 0.95}
    })
    
    ext = Extractions(
        package_id="pkg_test_approved",
        document_type="bank_paydown",
        extraction_json=dummy_extraction_json,
        confidence_score=0.95,
        is_reviewed=True
    )
    
    session.add_all([pkg1, pkg2, ext])
    session.commit()
    
    yield session
    
    session.close()
    try:
        Base.metadata.drop_all(engine)
    except Exception:
        pass

@pytest.fixture(scope="function")
def seed_db_with_extraction():
    engine = create_engine("sqlite:///test_e2e.db")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    pkg = Package(id="pkg_reviewer_test", original_filename="reviewer_test.zip", status="EXTRACTED")
    
    # Add a mock file record (1x1 white PNG)
    file_record = ExtractedFile(
        package_id="pkg_reviewer_test",
        filename="test_page.png",
        content=b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xdcD\xfe\xe7\x00\x00\x00\x00IEND\xaeB`\x82",
        mime_type="image/png"
    )
    session.add(file_record)
    session.flush() # Get file_record.id
    
    dummy_extraction_json = json.dumps({
        "lender_name": {"value": "Original Bank", "confidence": 0.9, "bbox": {"coordinates": [100, 100, 200, 200]}},
        "total_amount": {"value": 1000.50, "confidence": 0.8, "bbox": {"coordinates": [300, 100, 400, 400]}},
        "effective_date": {"value": "2023-01-01", "confidence": 0.95, "bbox": {"coordinates": [500, 100, 600, 300]}},
    })
    
    ext = Extractions(
        package_id="pkg_reviewer_test",
        file_id=file_record.id,
        document_type="bank_paydown",
        extraction_json=dummy_extraction_json,
        confidence_score=0.9,
        is_reviewed=False
    )
    
    session.add(pkg)
    session.add(ext)
    session.commit()
    
    yield session
    
    session.close()
    try:
        Base.metadata.drop_all(engine)
    except Exception:
        pass
