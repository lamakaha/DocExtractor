from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from src.models.schema import ExtractionJob
from src.utils.logging_utils import log_package_event


class ExtractionJobService:
    JOB_TYPE = "EXTRACT_PACKAGE"
    ACTIVE_STATUSES = {"PENDING", "PROCESSING"}

    def __init__(self, lease_seconds: int = 900, max_attempts: int = 3):
        self.lease_seconds = lease_seconds
        self.max_attempts = max_attempts

    def enqueue_package(self, session: Session, package_id: str) -> ExtractionJob:
        job = (
            session.query(ExtractionJob)
            .filter(
                ExtractionJob.package_id == package_id,
                ExtractionJob.job_type == self.JOB_TYPE,
            )
            .first()
        )

        if job:
            if job.status in self.ACTIVE_STATUSES:
                return job
            if job.status == "FAILED" and job.attempts < job.max_attempts:
                job.status = "PENDING"
                job.last_error = None
                job.claimed_by = None
                job.claimed_at = None
                job.lease_expires_at = None
                session.commit()
                log_package_event(package_id, "QUEUE", f"Requeued extraction job {job.id}")
                return job
            return job

        job = ExtractionJob(
            package_id=package_id,
            job_type=self.JOB_TYPE,
            status="PENDING",
            max_attempts=self.max_attempts,
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        log_package_event(package_id, "QUEUE", f"Queued extraction job {job.id}")
        return job

    def claim_next_job(self, session: Session, worker_id: str) -> Optional[ExtractionJob]:
        now = datetime.utcnow()
        pending_job = (
            session.query(ExtractionJob)
            .filter(
                ExtractionJob.job_type == self.JOB_TYPE,
                ExtractionJob.status == "PENDING",
            )
            .order_by(ExtractionJob.created_at.asc(), ExtractionJob.id.asc())
            .first()
        )
        if not pending_job:
            pending_job = (
                session.query(ExtractionJob)
                .filter(
                    ExtractionJob.job_type == self.JOB_TYPE,
                    ExtractionJob.status == "PROCESSING",
                    ExtractionJob.lease_expires_at.isnot(None),
                    ExtractionJob.lease_expires_at < now,
                )
                .order_by(ExtractionJob.updated_at.asc(), ExtractionJob.id.asc())
                .first()
            )
        if not pending_job:
            return None

        pending_job.status = "PROCESSING"
        pending_job.claimed_by = worker_id
        pending_job.claimed_at = now
        pending_job.lease_expires_at = now + timedelta(seconds=self.lease_seconds)
        pending_job.attempts += 1
        session.commit()
        session.refresh(pending_job)
        log_package_event(
            pending_job.package_id,
            "QUEUE",
            f"Claimed extraction job {pending_job.id} (attempt {pending_job.attempts}/{pending_job.max_attempts})",
        )
        return pending_job

    def complete_job(self, session: Session, job_id: int):
        job = session.query(ExtractionJob).filter(ExtractionJob.id == job_id).first()
        if not job:
            return
        job.status = "COMPLETED"
        job.claimed_by = None
        job.claimed_at = None
        job.lease_expires_at = None
        job.last_error = None
        session.commit()
        log_package_event(job.package_id, "QUEUE", f"Completed extraction job {job.id}", level="SUCCESS")

    def fail_job(self, session: Session, job_id: int, error: str):
        job = session.query(ExtractionJob).filter(ExtractionJob.id == job_id).first()
        if not job:
            return

        job.last_error = error
        job.claimed_by = None
        job.claimed_at = None
        job.lease_expires_at = None
        if job.attempts < job.max_attempts:
            job.status = "PENDING"
            session.commit()
            log_package_event(
                job.package_id,
                "QUEUE",
                f"Extraction job {job.id} failed and was requeued: {error}",
                level="WARNING",
            )
            return

        job.status = "FAILED"
        session.commit()
        log_package_event(
            job.package_id,
            "QUEUE",
            f"Extraction job {job.id} exhausted retries: {error}",
            level="ERROR",
        )
