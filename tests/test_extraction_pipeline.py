import json

from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.schema import Base, ExtractedFile, Extractions, Package
from src.models.triplets import BoundingBox, ExtractionResult, Triplet
from src.services.extraction_pipeline import ExtractionPipeline


def test_process_package_creates_canonical_pdf_and_persists_normalized_bboxes(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        package = Package(id="pkg1", original_filename="sample.txt", status="INGESTED")
        session.add(package)
        source_file = ExtractedFile(
            package_id=package.id,
            filename="sample.txt",
            original_path="sample.txt",
            content=b"hello from text source",
            extracted_text="hello from text source",
            mime_type="text/plain",
            size=22,
        )
        session.add(source_file)
        session.commit()
        package_id = package.id
        source_file_id = source_file.id

        monkeypatch.setattr("src.services.extraction_pipeline.db_session", lambda: session)
        monkeypatch.setattr("src.services.extraction_pipeline.log_package_event", lambda *args, **kwargs: None)
        monkeypatch.setattr(
            "src.services.extraction_pipeline.convert_from_bytes",
            lambda content: [Image.new("RGB", (120, 200), "white")],
        )

        pipeline = ExtractionPipeline()
        monkeypatch.setattr(
            pipeline.classification_service,
            "classify",
            lambda content, mime_type: "Commercial_Loan_Paydown",
        )
        monkeypatch.setattr(
            pipeline.extraction_service,
            "extract",
            lambda **kwargs: ExtractionResult(
                document_type="Commercial_Loan_Paydown",
                fields={
                    "lender_name": Triplet(
                        value="Test Bank",
                        confidence=0.95,
                        bbox=BoundingBox(coordinates=[10, 20, 30, 40]),
                    )
                },
            ),
        )

        pipeline.process_package(package_id)

        session.expire_all()
        files = session.query(ExtractedFile).filter(ExtractedFile.package_id == package_id).all()
        canonical_files = [file_record for file_record in files if file_record.original_path == f"canonical://{source_file_id}"]
        assert len(canonical_files) == 1
        assert canonical_files[0].mime_type == "application/pdf"

        extraction = session.query(Extractions).filter(Extractions.package_id == package_id).one()
        assert extraction.file_id == canonical_files[0].id
        assert extraction.document_type == "Commercial_Loan_Paydown"

        extraction_json = json.loads(extraction.extraction_json)
        assert extraction_json["lender_name"]["bbox"]["coordinates"] == [10, 20, 30, 40]
    finally:
        session.close()
        engine.dispose()
