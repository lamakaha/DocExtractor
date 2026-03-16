import os
import json
import asyncio
import io
import glob
import logging
from typing import List, Dict, Any, Optional
from pdf2image import convert_from_bytes
from sqlalchemy.orm import Session
from src.db.session import db_session
from src.models.schema import Package, ExtractedFile, Extractions
from src.services.classification_service import ClassificationService
from src.services.canonical_document_service import CanonicalDocumentService
from src.services.extraction_service import ExtractionService
from src.utils.logging_utils import log_package_event

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExtractionPipeline:
    def __init__(self, configs_path: str = "configs"):
        self.classification_service = ClassificationService(configs_path=configs_path)
        self.canonical_document_service = CanonicalDocumentService()
        self.extraction_service = ExtractionService()
        self.configs_path = configs_path

    def _load_schema(self, doc_type: str) -> Optional[Dict[str, Any]]:
        """Loads extraction schema for the given document type."""
        config_files = glob.glob(os.path.join(self.configs_path, "*.json"))
        for config_file in config_files:
            try:
                with open(config_file, "r") as f:
                    config = json.load(f)
                    if config.get("document_type") == doc_type:
                        return config.get("extraction_schema")
            except (json.JSONDecodeError, OSError) as e:
                logger.error(f"Error loading config {config_file}: {e}")
        return None

    def _select_primary_document(self, files: List[ExtractedFile]) -> Optional[ExtractedFile]:
        main_document_file = None
        visual_mimes = ["application/pdf", "image/png", "image/jpeg", "image/webp"]
        textual_mimes = ["text/plain", "text/html", "text/csv"]

        for file_record in files:
            if file_record.mime_type in textual_mimes and not main_document_file:
                main_document_file = file_record
            elif file_record.mime_type in visual_mimes:
                if not main_document_file or main_document_file.mime_type in textual_mimes:
                    main_document_file = file_record
        return main_document_file

    def _get_or_create_canonical_file(
        self,
        session: Session,
        package_id: str,
        source_file: ExtractedFile,
    ) -> ExtractedFile:
        if source_file.mime_type == "application/pdf":
            return source_file

        marker = f"canonical://{source_file.id}"
        existing = (
            session.query(ExtractedFile)
            .filter(
                ExtractedFile.package_id == package_id,
                ExtractedFile.original_path == marker,
                ExtractedFile.mime_type == "application/pdf",
            )
            .first()
        )
        if existing:
            return existing

        source_text = source_file.extracted_text
        if not source_text and source_file.mime_type in self.canonical_document_service.TEXTUAL_MIME_TYPES:
            source_text = source_file.content.decode("utf-8", errors="ignore") if source_file.content else ""

        pdf_bytes = self.canonical_document_service.build_canonical_pdf(
            content=source_file.content,
            mime_type=source_file.mime_type,
            filename=source_file.filename,
            extracted_text=source_text,
        )

        canonical_file = ExtractedFile(
            package_id=package_id,
            filename=self.canonical_document_service.canonical_filename(source_file.filename),
            original_path=marker,
            content=pdf_bytes,
            extracted_text=None,
            mime_type="application/pdf",
            size=len(pdf_bytes),
        )
        session.add(canonical_file)
        session.flush()
        return canonical_file

    def process_package(self, package_id: str) -> bool:
        """
        Orchestrates the full extraction flow for a single package.
        """
        session: Session = db_session()
        package = session.query(Package).filter(Package.id == package_id).first()
        if not package:
            logger.error(f"Package {package_id} not found.")
            return False

        log_package_event(package_id, "PIPELINE", f"Started pipeline for {package.original_filename}")

        try:
            # 1. Fetch extracted files
            files = session.query(ExtractedFile).filter(ExtractedFile.package_id == package_id).all()
            if not files:
                log_package_event(package_id, "PIPELINE", "No files found for package", level="WARNING", new_status="FAILED")
                return False

            # 2. Primary document selection and canonicalization
            log_package_event(package_id, "PIPELINE", f"Preparing package for classification (found {len(files)} files)")
            main_document_file = self._select_primary_document(files)
            if not main_document_file:
                log_package_event(package_id, "PIPELINE", "No processable document found in package", level="ERROR", new_status="FAILED")
                return False

            log_package_event(package_id, "PIPELINE", f"Selected '{main_document_file.filename}' as primary document")
            canonical_file = self._get_or_create_canonical_file(session, package_id, main_document_file)
            log_package_event(package_id, "CANONICALIZATION", f"Using '{canonical_file.filename}' as canonical PDF")

            # Prepare canonical PDF pages for extraction
            items_to_process = []
            log_package_event(package_id, "PIPELINE", "Converting canonical PDF to images for processing")
            try:
                pdf_pages = convert_from_bytes(canonical_file.content)
                for i, page in enumerate(pdf_pages):
                    img_byte_arr = io.BytesIO()
                    page.save(img_byte_arr, format="PNG")
                    items_to_process.append(
                        {
                            "content": img_byte_arr.getvalue(),
                            "mime_type": "image/png",
                            "width": page.width,
                            "height": page.height,
                            "file_id": canonical_file.id,
                            "page_num": i + 1,
                        }
                    )
                log_package_event(package_id, "PIPELINE", f"Converted canonical PDF to {len(items_to_process)} pages")
            except Exception as e:
                log_package_event(package_id, "PIPELINE", f"Canonical PDF conversion failed: {str(e)}", level="ERROR")
                raise

            # 3. Classification
            log_package_event(package_id, "CLASSIFICATION", "Starting document classification", new_status="CLASSIFYING")
            first_item = items_to_process[0]
            doc_type = self.classification_service.classify(
                content=first_item["content"],
                mime_type=first_item["mime_type"]
            )
            
            if doc_type == "UNKNOWN":
                log_package_event(package_id, "CLASSIFICATION", "Document type UNKNOWN", level="WARNING", new_status="FAILED")
                return False

            log_package_event(package_id, "CLASSIFICATION", f"Document classified as '{doc_type}'", level="SUCCESS")

            # 4. Extraction
            log_package_event(package_id, "EXTRACTION", f"Starting extraction for type '{doc_type}'", new_status="EXTRACTING")
            schema = self._load_schema(doc_type)
            if not schema:
                log_package_event(package_id, "EXTRACTION", f"No extraction schema found for type {doc_type}", level="ERROR", new_status="FAILED")
                return False

            all_results = []
            for item_data in items_to_process:
                page_info = f" (Page {item_data['page_num']})" if item_data['page_num'] > 1 else ""
                log_package_event(package_id, "EXTRACTION", f"Extracting data{page_info}")
                
                result = self.extraction_service.extract(
                    content=item_data["content"],
                    mime_type=item_data["mime_type"],
                    doc_type=doc_type,
                    extraction_schema=schema
                )

                # 5. Keep normalized bboxes as the persisted source of truth.
                result_dict = {name: triplet.model_dump() for name, triplet in result.fields.items()}

                # Calculate aggregate confidence
                confidences = [t["confidence"] for t in result_dict.values() if isinstance(t, dict) and "confidence" in t]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

                # 6. Persistence
                extraction_record = Extractions(
                    package_id=package_id,
                    file_id=item_data["file_id"],
                    document_type=doc_type,
                    extraction_json=json.dumps(result_dict),
                    confidence_score=avg_confidence
                )
                session.add(extraction_record)
                all_results.append(result_dict)

            # Update package status
            session.commit()
            log_package_event(package_id, "EXTRACTION", "Extraction completed successfully", level="SUCCESS", new_status="EXTRACTED")
            log_package_event(package_id, "PIPELINE", "Pipeline completed successfully", level="SUCCESS")
            return True

        except Exception as e:
            log_package_event(package_id, "PIPELINE", f"Pipeline failed: {str(e)}", level="ERROR", new_status="FAILED")
            session.rollback()
            return False
        finally:
            session.close()

    async def process_packages_parallel(self, package_ids: List[str], max_workers: int = 5):
        """
        Processes multiple packages concurrently.
        """
        semaphore = asyncio.Semaphore(max_workers)

        async def worker(package_id):
            async with semaphore:
                # Use to_thread for CPU-bound or blocking I/O (like DB and LLM calls)
                return await asyncio.to_thread(self.process_package, package_id)

        tasks = [worker(pid) for pid in package_ids]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    # Simple test run if called directly
    pipeline = ExtractionPipeline()
    print("Pipeline initialized.")
