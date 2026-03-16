import json
from typing import Any, List, Optional
from src.db.session import db_session
from src.models.schema import Package, Extractions, ExtractedFile, PackageLog, ExtractionJob

def get_all_packages(status_filter: Optional[List[str]] = None, include_archived: bool = False) -> List[Package]:
    """Fetch all packages, optionally filtered by status and archive state."""
    query = db_session.query(Package)
    
    if not include_archived:
        query = query.filter(Package.is_archived == False)
        
    if status_filter:
        query = query.filter(Package.status.in_(status_filter))
        
    return query.order_by(Package.created_at.desc()).all()

def get_package_by_id(package_id: str) -> Optional[Package]:
    """Fetch a single package by its ID."""
    return db_session.query(Package).filter(Package.id == package_id).first()

def get_extractions_for_package(package_id: str) -> List[Extractions]:
    """Fetch all extraction records associated with a package."""
    return db_session.query(Extractions).filter(Extractions.package_id == package_id).all()

def get_files_for_package(package_id: str) -> List[ExtractedFile]:
    """Fetch all files associated with a package."""
    return db_session.query(ExtractedFile).filter(ExtractedFile.package_id == package_id).all()

def get_package_logs(package_id: str) -> List[PackageLog]:
    """Fetch all logs for a specific package."""
    return db_session.query(PackageLog).filter(PackageLog.package_id == package_id).order_by(PackageLog.timestamp.asc()).all()

def parse_log_details(details: Optional[str]) -> Optional[Any]:
    """Parse structured log details JSON when available; otherwise return the raw string."""
    if not details:
        return None
    try:
        return json.loads(details)
    except (TypeError, json.JSONDecodeError):
        return details

def get_latest_extraction_job(package_id: str) -> Optional[ExtractionJob]:
    """Fetch the most recent extraction job for a package if one exists."""
    return (
        db_session.query(ExtractionJob)
        .filter(ExtractionJob.package_id == package_id)
        .order_by(ExtractionJob.created_at.desc(), ExtractionJob.id.desc())
        .first()
    )

def update_extraction(extraction_id: int, updated_json: str, is_reviewed: bool = True):
    """Update extraction JSON and mark as reviewed."""
    extraction = db_session.query(Extractions).filter(Extractions.id == extraction_id).first()
    if extraction:
        extraction.extraction_json = updated_json
        extraction.is_reviewed = is_reviewed
        db_session.commit()

def update_package_status(package_id: str, status: str):
    """Update the status of a package."""
    package = db_session.query(Package).filter(Package.id == package_id).first()
    if package:
        package.status = status
        db_session.commit()

def archive_package(package_id: str, archive: bool = True):
    """Mark a package as archived or unarchived."""
    package = db_session.query(Package).filter(Package.id == package_id).first()
    if package:
        package.is_archived = archive
        db_session.commit()

def archive_multiple_packages(package_ids: List[str], archive: bool = True):
    """Mark multiple packages as archived or unarchived."""
    db_session.query(Package).filter(Package.id.in_(package_ids)).update({"is_archived": archive}, synchronize_session=False)
    db_session.commit()
