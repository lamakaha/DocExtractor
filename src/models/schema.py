import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Package(Base):
    __tablename__ = "packages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    original_filename = Column(String, nullable=False)
    # Statuses: PENDING, INGESTING, INGESTED, CLASSIFYING, EXTRACTING, EXTRACTED, FAILED, APPROVED
    status = Column(String, default="PENDING")
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    extracted_files = relationship("ExtractedFile", back_populates="package", cascade="all, delete-orphan")
    logs = relationship("PackageLog", back_populates="package", cascade="all, delete-orphan")
    extraction_jobs = relationship("ExtractionJob", back_populates="package", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Package(id={self.id}, original_filename={self.original_filename}, status={self.status}, archived={self.is_archived})>"

class PackageLog(Base):
    __tablename__ = "package_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    package_id = Column(String(36), ForeignKey("packages.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    level = Column(String, default="INFO") # INFO, WARNING, ERROR, SUCCESS
    stage = Column(String, nullable=False) # INGESTION, CLASSIFICATION, EXTRACTION, PIPELINE
    message = Column(Text, nullable=False)
    details = Column(Text, nullable=True) # Extra JSON or text data

    package = relationship("Package", back_populates="logs")

    def __repr__(self):
        return f"<PackageLog(package_id={self.package_id}, stage={self.stage}, message={self.message})>"

class ExtractedFile(Base):
    __tablename__ = "extracted_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    package_id = Column(String(36), ForeignKey("packages.id"), nullable=False)
    filename = Column(String, nullable=False)
    original_path = Column(String)  # Nested path inside archive
    content = Column(LargeBinary)
    extracted_text = Column(Text)  # For email bodies
    mime_type = Column(String)
    size = Column(Integer)
    width = Column(Integer)  # For image/PDF dimensions
    height = Column(Integer) # For image/PDF dimensions

    package = relationship("Package", back_populates="extracted_files")
    extractions = relationship("Extractions", back_populates="file", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ExtractedFile(id={self.id}, filename={self.filename}, package_id={self.package_id})>"

class Extractions(Base):
    __tablename__ = "extractions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    package_id = Column(String(36), ForeignKey("packages.id"), nullable=False)
    file_id = Column(Integer, ForeignKey("extracted_files.id"), nullable=True) # Null for package-level extractions
    document_type = Column(String, nullable=False)
    extraction_json = Column(Text) # JSON string of raw triplets
    confidence_score = Column(Float) # Aggregate confidence
    is_reviewed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    package = relationship("Package")
    file = relationship("ExtractedFile", back_populates="extractions")

    def __repr__(self):
        return f"<Extractions(id={self.id}, package_id={self.package_id}, type={self.document_type})>"


class ExtractionJob(Base):
    __tablename__ = "extraction_jobs"
    __table_args__ = (UniqueConstraint("package_id", "job_type", name="uq_extraction_jobs_package_job_type"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    package_id = Column(String(36), ForeignKey("packages.id"), nullable=False)
    job_type = Column(String, nullable=False, default="EXTRACT_PACKAGE")
    status = Column(String, nullable=False, default="PENDING")
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    claimed_by = Column(String, nullable=True)
    claimed_at = Column(DateTime, nullable=True)
    lease_expires_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    package = relationship("Package", back_populates="extraction_jobs")

    def __repr__(self):
        return (
            f"<ExtractionJob(id={self.id}, package_id={self.package_id}, job_type={self.job_type}, "
            f"status={self.status}, attempts={self.attempts})>"
        )
