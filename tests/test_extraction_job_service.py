from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.schema import Base, ExtractionJob, Package
from src.services.extraction_job_service import ExtractionJobService


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    return engine, session


def test_enqueue_package_is_idempotent(monkeypatch):
    engine, session = make_session()
    try:
        monkeypatch.setattr("src.services.extraction_job_service.log_package_event", lambda *args, **kwargs: None)
        session.add(Package(id="pkg1", original_filename="sample.zip", status="INGESTED"))
        session.commit()

        service = ExtractionJobService()
        job1 = service.enqueue_package(session, "pkg1")
        job2 = service.enqueue_package(session, "pkg1")

        assert job1.id == job2.id
        assert session.query(ExtractionJob).count() == 1
        assert job1.status == "PENDING"
    finally:
        session.close()
        engine.dispose()


def test_enqueue_package_does_not_revive_dead_letter_job(monkeypatch):
    engine, session = make_session()
    try:
        monkeypatch.setattr("src.services.extraction_job_service.log_package_event", lambda *args, **kwargs: None)
        session.add(Package(id="pkg1", original_filename="sample.zip", status="INGESTED"))
        session.commit()

        dead_letter_job = ExtractionJob(
            package_id="pkg1",
            job_type="EXTRACT_PACKAGE",
            status="DEAD_LETTER",
            attempts=3,
            max_attempts=3,
            last_error="permanent failure",
        )
        session.add(dead_letter_job)
        session.commit()

        service = ExtractionJobService()
        job = service.enqueue_package(session, "pkg1")
        session.refresh(dead_letter_job)

        assert job.id == dead_letter_job.id
        assert dead_letter_job.status == "DEAD_LETTER"
        assert session.query(ExtractionJob).count() == 1
    finally:
        session.close()
        engine.dispose()


def test_claim_next_job_sets_attempt_and_lease(monkeypatch):
    engine, session = make_session()
    try:
        monkeypatch.setattr("src.services.extraction_job_service.log_package_event", lambda *args, **kwargs: None)
        session.add(Package(id="pkg1", original_filename="sample.zip", status="INGESTED"))
        session.commit()

        service = ExtractionJobService(lease_seconds=60)
        service.enqueue_package(session, "pkg1")

        claimed = service.claim_next_job(session, "worker-1")

        assert claimed is not None
        assert claimed.status == "PROCESSING"
        assert claimed.attempts == 1
        assert claimed.claimed_by == "worker-1"
        assert claimed.lease_expires_at is not None
    finally:
        session.close()
        engine.dispose()


def test_fail_job_requeues_until_max_attempts(monkeypatch):
    engine, session = make_session()
    try:
        monkeypatch.setattr("src.services.extraction_job_service.log_package_event", lambda *args, **kwargs: None)
        session.add(Package(id="pkg1", original_filename="sample.zip", status="INGESTED"))
        session.commit()

        service = ExtractionJobService(max_attempts=2)
        job = service.enqueue_package(session, "pkg1")

        claimed = service.claim_next_job(session, "worker-1")
        service.fail_job(session, claimed.id, "first failure")
        session.refresh(job)
        assert job.status == "PENDING"
        assert job.last_error == "first failure"

        claimed = service.claim_next_job(session, "worker-1")
        service.fail_job(session, claimed.id, "second failure")
        session.refresh(job)
        assert job.status == "DEAD_LETTER"
        assert job.attempts == 2
    finally:
        session.close()
        engine.dispose()


def test_claim_next_job_reclaims_expired_processing_job(monkeypatch):
    engine, session = make_session()
    try:
        monkeypatch.setattr("src.services.extraction_job_service.log_package_event", lambda *args, **kwargs: None)
        session.add(Package(id="pkg1", original_filename="sample.zip", status="INGESTED"))
        session.commit()

        expired_job = ExtractionJob(
            package_id="pkg1",
            job_type="EXTRACT_PACKAGE",
            status="PROCESSING",
            attempts=1,
            max_attempts=3,
            claimed_by="old-worker",
            claimed_at=datetime.utcnow() - timedelta(minutes=10),
            lease_expires_at=datetime.utcnow() - timedelta(minutes=5),
        )
        session.add(expired_job)
        session.commit()

        service = ExtractionJobService()
        claimed = service.claim_next_job(session, "worker-2")

        assert claimed is not None
        assert claimed.id == expired_job.id
        assert claimed.status == "PROCESSING"
        assert claimed.claimed_by == "worker-2"
        assert claimed.attempts == 2
    finally:
        session.close()
        engine.dispose()


def test_recover_stale_job_moves_to_pending_before_reclaim(monkeypatch):
    engine, session = make_session()
    try:
        monkeypatch.setattr("src.services.extraction_job_service.log_package_event", lambda *args, **kwargs: None)
        session.add(Package(id="pkg1", original_filename="sample.zip", status="INGESTED"))
        session.commit()

        stale_job = ExtractionJob(
            package_id="pkg1",
            job_type="EXTRACT_PACKAGE",
            status="PROCESSING",
            attempts=1,
            max_attempts=3,
            claimed_by="dead-worker",
            claimed_at=datetime.utcnow() - timedelta(minutes=10),
            lease_expires_at=datetime.utcnow() - timedelta(minutes=5),
        )
        session.add(stale_job)
        session.commit()

        service = ExtractionJobService()
        recovered = service.recover_stale_jobs(session)
        session.refresh(stale_job)

        assert recovered == 1
        assert stale_job.status == "PENDING"
        assert stale_job.claimed_by is None
        assert stale_job.lease_expires_at is None
    finally:
        session.close()
        engine.dispose()


def test_recover_stale_job_dead_letters_when_retry_budget_exhausted(monkeypatch):
    engine, session = make_session()
    try:
        monkeypatch.setattr("src.services.extraction_job_service.log_package_event", lambda *args, **kwargs: None)
        session.add(Package(id="pkg1", original_filename="sample.zip", status="INGESTED"))
        session.commit()

        stale_job = ExtractionJob(
            package_id="pkg1",
            job_type="EXTRACT_PACKAGE",
            status="PROCESSING",
            attempts=3,
            max_attempts=3,
            claimed_by="dead-worker",
            claimed_at=datetime.utcnow() - timedelta(minutes=10),
            lease_expires_at=datetime.utcnow() - timedelta(minutes=5),
            last_error="worker crashed mid-run",
        )
        session.add(stale_job)
        session.commit()

        service = ExtractionJobService()
        recovered = service.recover_stale_jobs(session)
        next_job = service.claim_next_job(session, "worker-2")
        session.refresh(stale_job)

        assert recovered == 1
        assert stale_job.status == "DEAD_LETTER"
        assert stale_job.claimed_by is None
        assert next_job is None
    finally:
        session.close()
        engine.dispose()
