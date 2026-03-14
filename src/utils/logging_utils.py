import json
import logging
from datetime import datetime
from typing import Optional, Any
from src.db.session import SessionLocal
from src.models.schema import Package, PackageLog

logger = logging.getLogger(__name__)

def log_package_event(
    package_id: str,
    stage: str,
    message: str,
    level: str = "INFO",
    details: Optional[Any] = None,
    new_status: Optional[str] = None
):
    """
    Logs an event for a specific package and optionally updates its status.
    Uses a fresh session to ensure logs are committed even if the main transaction rolls back.
    """
    session = SessionLocal()
    try:
        # 1. Update status if requested
        if new_status:
            package = session.query(Package).filter(Package.id == package_id).first()
            if package:
                package.status = new_status
        
        # 2. Create log entry
        details_str = None
        if details:
            if isinstance(details, (dict, list)):
                details_str = json.dumps(details)
            else:
                details_str = str(details)
                
        log_entry = PackageLog(
            package_id=package_id,
            stage=stage,
            message=message,
            level=level,
            details=details_str,
            timestamp=datetime.utcnow()
        )
        session.add(log_entry)
        session.commit()
        
        # Also log to standard python logger
        log_msg = f"[{stage}] [{package_id}] {message}"
        if level == "ERROR":
            logger.error(log_msg)
        elif level == "WARNING":
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
            
    except Exception as e:
        logger.error(f"Failed to log package event for {package_id}: {e}")
        session.rollback()
    finally:
        session.close()
