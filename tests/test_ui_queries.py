import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models.schema import Base, Package, Extractions, ExtractionJob, PackageLog
from src.ui import db_utils
from src.db.session import db_session

# Test database setup
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    # Override the engine and session for tests
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    
    # Patch the global db_session
    # Since db_utils uses db_session, we need to ensure it's pointing to our test db
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # This is a bit tricky if we don't have a way to inject the session.
    # But since it's a scoped session, we can probably just configure it.
    # Alternatively, let's just use the current session and clean up.
    
    # For now, let's try to patch db_session if possible, or just use it.
    # Actually, the simplest way is to manually add data to whatever db_session is currently using if we can control it.
    
    yield session
    
    Base.metadata.drop_all(bind=engine)

def test_get_all_packages(setup_test_db):
    session = setup_test_db
    # Clear existing data
    session.query(Package).delete()
    
    # Add dummy data
    p1 = Package(id="1", original_filename="test1.zip", status="INGESTED")
    p2 = Package(id="2", original_filename="test2.zip", status="EXTRACTED")
    p3 = Package(id="3", original_filename="test3.zip", status="APPROVED")
    session.add_all([p1, p2, p3])
    session.commit()
    
    # We need to make sure db_utils.db_session uses this session or we mock it.
    # Let's mock the db_session in db_utils.
    import src.ui.db_utils as dbu
    old_session = dbu.db_session
    dbu.db_session = session
    
    try:
        packages = dbu.get_all_packages()
        assert len(packages) == 3
        
        ingested = dbu.get_all_packages(status_filter=["INGESTED"])
        assert len(ingested) == 1
        assert ingested[0].id == "1"
        
        filtered = dbu.get_all_packages(status_filter=["EXTRACTED", "APPROVED"])
        assert len(filtered) == 2
    finally:
        dbu.db_session = old_session

def test_get_package_by_id(setup_test_db):
    session = setup_test_db
    import src.ui.db_utils as dbu
    old_session = dbu.db_session
    dbu.db_session = session
    
    try:
        p = dbu.get_package_by_id("2")
        assert p is not None
        assert p.original_filename == "test2.zip"
        
        p_none = dbu.get_package_by_id("non-existent")
        assert p_none is None
    finally:
        dbu.db_session = old_session

def test_get_extractions_for_package(setup_test_db):
    session = setup_test_db
    import src.ui.db_utils as dbu
    old_session = dbu.db_session
    dbu.db_session = session
    
    try:
        # Add extraction
        e1 = Extractions(package_id="2", document_type="Bank Paydown", extraction_json="{}", confidence_score=0.9)
        session.add(e1)
        session.commit()
        
        extractions = dbu.get_extractions_for_package("2")
        assert len(extractions) == 1
        assert extractions[0].document_type == "Bank Paydown"
        
        empty = dbu.get_extractions_for_package("1")
        assert len(empty) == 0
    finally:
        dbu.db_session = old_session

def test_archive_package(setup_test_db):
    session = setup_test_db
    import src.ui.db_utils as dbu
    old_session = dbu.db_session
    dbu.db_session = session
    try:
        p = Package(id='4', original_filename='test4.zip', status='FAILED')
        session.add(p)
        session.commit()
        dbu.archive_package('4', True)
        assert dbu.get_package_by_id('4').is_archived == True
        assert len(dbu.get_all_packages(include_archived=False, status_filter=['FAILED'])) == 0
        dbu.archive_package('4', False)
        assert dbu.get_package_by_id('4').is_archived == False
        assert len(dbu.get_all_packages(include_archived=False, status_filter=['FAILED'])) == 1
    finally:
        dbu.db_session = old_session

def test_archive_multiple_packages(setup_test_db):
    session = setup_test_db
    import src.ui.db_utils as dbu
    old_session = dbu.db_session
    dbu.db_session = session
    try:
        p1 = Package(id='5', original_filename='test5.zip', status='FAILED')
        p2 = Package(id='6', original_filename='test6.zip', status='FAILED')
        session.add_all([p1, p2])
        session.commit()
        dbu.archive_multiple_packages(['5', '6'], True)
        assert dbu.get_package_by_id('5').is_archived == True
        assert dbu.get_package_by_id('6').is_archived == True
    finally:
        dbu.db_session = old_session

def test_parse_log_details_and_latest_job(setup_test_db):
    session = setup_test_db
    import src.ui.db_utils as dbu
    old_session = dbu.db_session
    dbu.db_session = session
    try:
        pkg = Package(id="7", original_filename="diag.zip", status="FAILED")
        session.add(pkg)
        session.add(
            PackageLog(
                package_id="7",
                stage="EXTRACTION",
                message="failed",
                level="ERROR",
                details='{"model_id":"m1","latency_ms":12.5}',
            )
        )
        session.add(
            ExtractionJob(
                package_id="7",
                job_type="EXTRACT_PACKAGE",
                status="FAILED",
                attempts=2,
                max_attempts=3,
                last_error="boom",
            )
        )
        session.commit()

        parsed = dbu.parse_log_details('{"model_id":"m1","latency_ms":12.5}')
        assert parsed["model_id"] == "m1"
        assert dbu.parse_log_details("plain text") == "plain text"

        latest_job = dbu.get_latest_extraction_job("7")
        assert latest_job is not None
        assert latest_job.status == "FAILED"
        assert latest_job.last_error == "boom"
    finally:
        dbu.db_session = old_session
