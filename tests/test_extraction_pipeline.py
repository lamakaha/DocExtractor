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
        log_calls = []
        monkeypatch.setattr("src.services.extraction_pipeline.log_package_event", lambda *args, **kwargs: log_calls.append((args, kwargs)))
        monkeypatch.setattr(
            "src.services.extraction_pipeline.convert_from_bytes",
            lambda content: [Image.new("RGB", (120, 200), "white")],
        )

        pipeline = ExtractionPipeline()
        monkeypatch.setattr(
            pipeline.classification_service,
            "classify",
            lambda content, mime_type, text_context="": "Commercial_Loan_Paydown",
        )
        pipeline.classification_service.last_run_details = {"model_id": "test-model", "content_items": 1, "text_context_chars": 22}
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
                raw_response='{"lender_name":{"value":"Test Bank","confidence":0.95,"bbox":[10,20,30,40]}}',
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
        assert extraction_json["lender_name"]["page_number"] == 1
        assert any(call[0][1] == "CLASSIFICATION" and call[1].get("details", {}).get("model_id") == "test-model" for call in log_calls)
        extraction_detail_calls = [call for call in log_calls if call[0][1] == "EXTRACTION" and call[0][2] == "Extraction completed for page 1"]
        assert extraction_detail_calls
        assert extraction_detail_calls[0][1]["details"]["raw_response_chars"] > 0
        assert extraction_detail_calls[0][1]["details"]["raw_response_truncated"] is False
    finally:
        session.close()
        engine.dispose()


def test_process_package_reconciles_multi_page_results(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        package = Package(id="pkg2", original_filename="sample.pdf", status="INGESTED")
        session.add(package)
        source_file = ExtractedFile(
            package_id=package.id,
            filename="sample.pdf",
            original_path="sample.pdf",
            content=b"%PDF-1.4 fake",
            extracted_text=None,
            mime_type="application/pdf",
            size=13,
        )
        session.add(source_file)
        session.commit()
        package_id = package.id

        monkeypatch.setattr("src.services.extraction_pipeline.db_session", lambda: session)
        log_calls = []
        monkeypatch.setattr("src.services.extraction_pipeline.log_package_event", lambda *args, **kwargs: log_calls.append((args, kwargs)))
        monkeypatch.setattr(
            "src.services.extraction_pipeline.convert_from_bytes",
            lambda content: [Image.new("RGB", (120, 200), "white"), Image.new("RGB", (120, 200), "white")],
        )

        pipeline = ExtractionPipeline()
        monkeypatch.setattr(pipeline.classification_service, "classify", lambda content, mime_type, text_context="": "Commercial_Loan_Paydown")
        pipeline.classification_service.last_run_details = {"model_id": "test-model", "content_items": 2, "text_context_chars": 0}
        results = iter(
            [
                ExtractionResult(
                    document_type="Commercial_Loan_Paydown",
                    fields={
                        "lender_name": Triplet(value="", confidence=0.4, bbox=None),
                        "total_amount": Triplet(value="100", confidence=0.5, bbox=BoundingBox(coordinates=[10, 20, 30, 40])),
                    },
                    raw_response='{"page":1}',
                ),
                ExtractionResult(
                    document_type="Commercial_Loan_Paydown",
                    fields={
                        "lender_name": Triplet(value="Merged Bank", confidence=0.9, bbox=BoundingBox(coordinates=[50, 60, 70, 80])),
                        "total_amount": Triplet(value="90", confidence=0.4, bbox=BoundingBox(coordinates=[11, 21, 31, 41])),
                    },
                    raw_response='{"page":2}',
                ),
            ]
        )
        monkeypatch.setattr(pipeline.extraction_service, "extract", lambda **kwargs: next(results))
        pipeline.extraction_service.last_run_details = {"model_id": "test-model", "prompt_version": "extraction.v1.structured-json"}

        pipeline.process_package(package_id)

        extraction = session.query(Extractions).filter(Extractions.package_id == package_id).one()
        extraction_json = json.loads(extraction.extraction_json)
        assert extraction_json["lender_name"]["value"] == "Merged Bank"
        assert extraction_json["lender_name"]["page_number"] == 2
        assert extraction_json["total_amount"]["value"] == "100"
        assert extraction_json["total_amount"]["page_number"] == 1
        assert any(call[0][1] == "EXTRACTION" and isinstance(call[1].get("details"), dict) for call in log_calls)
    finally:
        session.close()
        engine.dispose()


def test_process_package_logs_explicit_package_selection_and_supporting_context(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        package = Package(id="pkg3", original_filename="mixed.zip", status="INGESTED")
        session.add(package)
        primary_pdf = ExtractedFile(
            package_id=package.id,
            filename="loan_paydown_notice.pdf",
            original_path="loan_paydown_notice.pdf",
            content=b"%PDF-1.4 primary",
            extracted_text=None,
            mime_type="application/pdf",
            size=4096,
        )
        supporting_text = ExtractedFile(
            package_id=package.id,
            filename="cover_email.txt",
            original_path="cover_email.txt",
            content=b"borrower requested payoff support",
            extracted_text="borrower requested payoff support",
            mime_type="text/plain",
            size=128,
        )
        supporting_pdf = ExtractedFile(
            package_id=package.id,
            filename="backup_statement.pdf",
            original_path="backup_statement.pdf",
            content=b"%PDF-1.4 support",
            extracted_text=None,
            mime_type="application/pdf",
            size=2048,
        )
        session.add_all([primary_pdf, supporting_text, supporting_pdf])
        session.commit()

        monkeypatch.setattr("src.services.extraction_pipeline.db_session", lambda: session)
        log_calls = []
        monkeypatch.setattr("src.services.extraction_pipeline.log_package_event", lambda *args, **kwargs: log_calls.append((args, kwargs)))

        def fake_convert(content, **kwargs):
            if content == primary_pdf.content:
                return [Image.new("RGB", (120, 200), "white")]
            return [Image.new("RGB", (60, 80), "white")]

        monkeypatch.setattr("src.services.extraction_pipeline.convert_from_bytes", fake_convert)

        pipeline = ExtractionPipeline()
        classification_calls = []

        def fake_classify(content, mime_type, text_context=""):
            classification_calls.append({"content": content, "mime_type": mime_type, "text_context": text_context})
            return "Commercial_Loan_Paydown"

        monkeypatch.setattr(pipeline.classification_service, "classify", fake_classify)
        pipeline.classification_service.last_run_details = {"model_id": "test-model", "content_items": 2, "text_context_chars": 0}
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
                raw_response='{"lender_name":{"value":"Test Bank"}}',
            ),
        )

        assert pipeline.process_package(package.id) is True

        pipeline_selection_logs = [call for call in log_calls if call[0][1] == "PIPELINE" and call[0][2].startswith("Selected")]
        assert len(pipeline_selection_logs) == 1
        selection_details = pipeline_selection_logs[0][1]["details"]
        assert selection_details["primary_document"] == "loan_paydown_notice.pdf"
        assert "backup_statement.pdf" in selection_details["supporting_visual"]
        assert "cover_email.txt" in selection_details["supporting_text"]

        assert len(classification_calls) == 1
        assert len(classification_calls[0]["content"]) == 2
        assert classification_calls[0]["mime_type"] == ["image/png", "image/png"]
        assert "Primary candidate: loan_paydown_notice.pdf (application/pdf)" in classification_calls[0]["text_context"]
        assert "Supporting textual artifacts: cover_email.txt (text/plain)" in classification_calls[0]["text_context"]
    finally:
        session.close()
        engine.dispose()
