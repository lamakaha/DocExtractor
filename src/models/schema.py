import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, ForeignKey, LargeBinary, Text, DateTime
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Package(Base):
    __tablename__ = "packages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    original_filename = Column(String, nullable=False)
    status = Column(String, default="INGESTED")  # INGESTED, EXTRACTED, APPROVED
    created_at = Column(DateTime, default=datetime.utcnow)

    extracted_files = relationship("ExtractedFile", back_populates="package", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Package(id={self.id}, original_filename={self.original_filename}, status={self.status})>"

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

    package = relationship("Package", back_populates="extracted_files")

    def __repr__(self):
        return f"<ExtractedFile(id={self.id}, filename={self.filename}, package_id={self.package_id})>"
