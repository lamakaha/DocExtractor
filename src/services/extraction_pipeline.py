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
from src.services.reconciliation_service import ReconciliationService
from src.utils.logging_utils import log_package_event

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExtractionPipeline:
    PRIMARY_HINT_TERMS = ("paydown", "statement", "notice", "loan", "demand", "invoice")
    DEPRIORITIZED_HINT_TERMS = ("copy", "duplicate", "backup", "notes", "cover", "summary")

    def __init__(self, configs_path: str = "configs"):
        self.classification_service = ClassificationService(configs_path=configs_path)
        self.canonical_document_service = CanonicalDocumentService()
        self.extraction_service = ExtractionService()
        self.reconciliation_service = ReconciliationService()
        self.configs_path = configs_path

    def _build_classification_context(
        self,
        files: List[ExtractedFile],
        items_to_process: List[Dict[str, Any]],
        selection: Dict[str, Any],
        max_pages: int = 2,
        max_supporting_visual_items: int = 1,
        max_text_chars: int = 1500,
    ) -> tuple[List[bytes], List[str], str]:
        page_contents = [item["content"] for item in items_to_process[:max_pages]]
        mime_types = [item["mime_type"] for item in items_to_process[:max_pages]]
        for support_file in selection.get("supporting_visual", [])[:max_supporting_visual_items]:
            preview = self._build_visual_preview_item(support_file)
            if preview:
                page_contents.append(preview["content"])
                mime_types.append(preview["mime_type"])

        text_parts: List[str] = [self._format_selection_manifest(selection)]
        remaining = max_text_chars
        for file_record in selection.get("supporting_text", []) + selection.get("ignored_textual", []):
            text = file_record.extracted_text
            if not text and file_record.mime_type in self.canonical_document_service.TEXTUAL_MIME_TYPES:
                text = file_record.content.decode("utf-8", errors="ignore") if file_record.content else ""
            if not text:
                continue
            snippet = text.strip()
            if not snippet:
                continue
            if len(snippet) > remaining:
                snippet = snippet[:remaining]
            if snippet:
                text_parts.append(f"{file_record.filename}: {snippet}")
                remaining -= len(snippet)
            if remaining <= 0:
                break
        return page_contents, mime_types, "\n\n".join(text_parts)

    def _build_extraction_audit_details(
        self,
        run_details: Dict[str, Any],
        page_number: int,
        raw_response: Optional[str],
        max_chars: int = 20000,
    ) -> Dict[str, Any]:
        audit_details = {**run_details, "page_number": page_number}
        if raw_response is None:
            return audit_details

        truncated = raw_response
        was_truncated = False
        if len(raw_response) > max_chars:
            truncated = raw_response[:max_chars]
            was_truncated = True

        audit_details["raw_response"] = truncated
        audit_details["raw_response_chars"] = len(raw_response)
        audit_details["raw_response_truncated"] = was_truncated
        return audit_details

    def _build_visual_preview_item(self, file_record: ExtractedFile) -> Optional[Dict[str, Any]]:
        try:
            if file_record.mime_type == "application/pdf":
                preview_page = convert_from_bytes(file_record.content, first_page=1, last_page=1)[0]
                img_byte_arr = io.BytesIO()
                preview_page.save(img_byte_arr, format="PNG")
                return {"content": img_byte_arr.getvalue(), "mime_type": "image/png"}
            if file_record.mime_type in self.canonical_document_service.IMAGE_MIME_TYPES:
                return {"content": file_record.content, "mime_type": file_record.mime_type}
        except Exception as exc:
            logger.warning("Failed to build supporting visual preview for %s: %s", file_record.filename, exc)
        return None

    def _is_canonical_derivative(self, file_record: ExtractedFile) -> bool:
        return bool(file_record.original_path and file_record.original_path.startswith("canonical://"))

    def _candidate_role_score(self, file_record: ExtractedFile) -> tuple[int, str]:
        mime_type = file_record.mime_type or ""
        filename = (file_record.filename or "").lower()
        score = 0
        role = "ignored"

        if mime_type == "application/pdf":
            score = 300
            role = "primary_candidate"
        elif mime_type in self.canonical_document_service.IMAGE_MIME_TYPES:
            score = 220
            role = "primary_candidate"
        elif mime_type == "text/plain":
            score = 120
            role = "supporting_text"
        elif mime_type == "text/html":
            score = 105
            role = "supporting_text"
        elif mime_type == "text/csv":
            score = 80
            role = "supporting_text"
        elif self.canonical_document_service.can_canonicalize(mime_type):
            score = 50
            role = "supporting_text"

        for term in self.PRIMARY_HINT_TERMS:
            if term in filename:
                score += 15
                break
        for term in self.DEPRIORITIZED_HINT_TERMS:
            if term in filename:
                score -= 20
                break
        if self._is_canonical_derivative(file_record):
            score -= 500
            role = "generated_artifact"
        if not self.canonical_document_service.can_canonicalize(mime_type):
            score -= 200
            role = "unsupported"
        if file_record.size:
            score += min(file_record.size // 1024, 10)

        return score, role

    def _select_package_documents(self, files: List[ExtractedFile]) -> Dict[str, Any]:
        selection: Dict[str, Any] = {
            "primary": None,
            "supporting_visual": [],
            "supporting_text": [],
            "ignored": [],
            "ignored_textual": [],
            "candidates": [],
        }
        ranked_candidates = []
        for file_record in files:
            score, role = self._candidate_role_score(file_record)
            selection["candidates"].append(
                {"filename": file_record.filename, "mime_type": file_record.mime_type, "score": score, "role": role}
            )
            if role in {"generated_artifact", "unsupported"}:
                selection["ignored"].append(file_record)
                if file_record.mime_type in self.canonical_document_service.TEXTUAL_MIME_TYPES:
                    selection["ignored_textual"].append(file_record)
                continue
            ranked_candidates.append((score, file_record))

        ranked_candidates.sort(
            key=lambda item: (
                item[0],
                1 if item[1].mime_type == "application/pdf" else 0,
                1 if item[1].mime_type in self.canonical_document_service.IMAGE_MIME_TYPES else 0,
            ),
            reverse=True,
        )

        if ranked_candidates:
            selection["primary"] = ranked_candidates[0][1]

        for _, candidate in ranked_candidates[1:]:
            if candidate.mime_type in {"application/pdf"} | self.canonical_document_service.IMAGE_MIME_TYPES:
                selection["supporting_visual"].append(candidate)
            elif candidate.mime_type in self.canonical_document_service.TEXTUAL_MIME_TYPES:
                selection["supporting_text"].append(candidate)
            else:
                selection["ignored"].append(candidate)

        return selection

    def _format_selection_manifest(self, selection: Dict[str, Any]) -> str:
        primary = selection.get("primary")
        primary_label = f"{primary.filename} ({primary.mime_type})" if primary else "None"
        supporting_visual = ", ".join(
            f"{file_record.filename} ({file_record.mime_type})" for file_record in selection.get("supporting_visual", [])
        ) or "None"
        supporting_text = ", ".join(
            f"{file_record.filename} ({file_record.mime_type})" for file_record in selection.get("supporting_text", [])
        ) or "None"
        ignored = ", ".join(
            f"{file_record.filename} ({file_record.mime_type})" for file_record in selection.get("ignored", [])
        ) or "None"
        return (
            "Package candidate selection:\n"
            f"- Primary candidate: {primary_label}\n"
            f"- Supporting visual candidates: {supporting_visual}\n"
            f"- Supporting textual artifacts: {supporting_text}\n"
            f"- Ignored artifacts: {ignored}"
        )

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
            selection = self._select_package_documents(files)
            main_document_file = selection["primary"]
            if not main_document_file:
                log_package_event(package_id, "PIPELINE", "No processable document found in package", level="ERROR", new_status="FAILED")
                return False

            log_package_event(
                package_id,
                "PIPELINE",
                f"Selected '{main_document_file.filename}' as primary document",
                details={
                    "primary_document": main_document_file.filename,
                    "supporting_visual": [file_record.filename for file_record in selection["supporting_visual"]],
                    "supporting_text": [file_record.filename for file_record in selection["supporting_text"]],
                    "ignored_artifacts": [file_record.filename for file_record in selection["ignored"]],
                    "candidate_scores": selection["candidates"],
                },
            )
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
            classification_contents, classification_mime_types, text_context = self._build_classification_context(
                files,
                items_to_process,
                selection,
            )
            doc_type = self.classification_service.classify(
                content=classification_contents,
                mime_type=classification_mime_types,
                text_context=text_context,
            )
            log_package_event(
                package_id,
                "CLASSIFICATION",
                f"Classification completed as '{doc_type}'",
                level="SUCCESS" if doc_type != "UNKNOWN" else "WARNING",
                details=self.classification_service.last_run_details,
            )
            
            if doc_type == "UNKNOWN":
                log_package_event(package_id, "CLASSIFICATION", "Document type UNKNOWN", level="WARNING", new_status="FAILED")
                return False

            # 4. Extraction
            log_package_event(package_id, "EXTRACTION", f"Starting extraction for type '{doc_type}'", new_status="EXTRACTING")
            schema = self._load_schema(doc_type)
            if not schema:
                log_package_event(package_id, "EXTRACTION", f"No extraction schema found for type {doc_type}", level="ERROR", new_status="FAILED")
                return False

            page_results = []
            for item_data in items_to_process:
                page_info = f" (Page {item_data['page_num']})" if item_data['page_num'] > 1 else ""
                log_package_event(package_id, "EXTRACTION", f"Extracting data{page_info}")
                
                result = self.extraction_service.extract(
                    content=item_data["content"],
                    mime_type=item_data["mime_type"],
                    doc_type=doc_type,
                    extraction_schema=schema
                )
                log_package_event(
                    package_id,
                    "EXTRACTION",
                    f"Extraction completed for page {item_data['page_num']}",
                    details=self._build_extraction_audit_details(
                        self.extraction_service.last_run_details,
                        page_number=item_data["page_num"],
                        raw_response=result.raw_response,
                    ),
                )

                # 5. Keep normalized bboxes as the persisted source of truth.
                result_dict = {}
                for name, triplet in result.fields.items():
                    payload = triplet.model_dump()
                    payload["page_number"] = item_data["page_num"]
                    result_dict[name] = payload
                page_results.append(result_dict)

            # 6. Reconciliation and persistence
            reconciled_result = self.reconciliation_service.reconcile(page_results)
            confidences = [t["confidence"] for t in reconciled_result.values() if isinstance(t, dict) and "confidence" in t]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            extraction_record = Extractions(
                package_id=package_id,
                file_id=canonical_file.id,
                document_type=doc_type,
                extraction_json=json.dumps(reconciled_result),
                confidence_score=avg_confidence
            )
            session.add(extraction_record)

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
