import os
import json
import asyncio
import io
import glob
import logging
from typing import List, Dict, Any, Optional
from PIL import Image
from pdf2image import convert_from_bytes
from sqlalchemy.orm import Session
from src.db.session import db_session
from src.models.schema import Package, ExtractedFile, Extractions
from src.models.triplets import Triplet, ExtractionResult
from src.services.classification_service import ClassificationService
from src.services.extraction_service import ExtractionService
from src.services.coordinate_scaler import CoordinateScaler
from src.utils.logging_utils import log_package_event

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExtractionPipeline:
    def __init__(self, configs_path: str = "configs"):
        self.classification_service = ClassificationService(configs_path=configs_path)
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

    def _scale_triplet_bboxes(self, data: Any, width: int, height: int) -> Any:
        """Recursively scales bboxes in triplets from normalized to pixel coordinates."""
        if isinstance(data, dict):
            # Check if this is a triplet-like dict
            if all(k in data for k in ["value", "confidence", "bbox"]):
                if data.get("bbox") and "coordinates" in data["bbox"]:
                    coords = data["bbox"]["coordinates"]
                    try:
                        scaled_coords = CoordinateScaler.normalize_to_pixel(coords, width, height)
                        data["bbox"]["coordinates"] = scaled_coords
                    except ValueError as e:
                        logger.warning(f"Scaling failed for bbox {coords}: {e}")
                
                # Recursively process value
                data["value"] = self._scale_triplet_bboxes(data["value"], width, height)
                return data
            else:
                return {k: self._scale_triplet_bboxes(v, width, height) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._scale_triplet_bboxes(item, width, height) for item in data]
        return data

    def process_package(self, package_id: str):
        """
        Orchestrates the full extraction flow for a single package.
        """
        session: Session = db_session()
        package = session.query(Package).filter(Package.id == package_id).first()
        if not package:
            logger.error(f"Package {package_id} not found.")
            return

        log_package_event(package_id, "PIPELINE", f"Started pipeline for {package.original_filename}")

        try:
            # 1. Fetch extracted files
            files = session.query(ExtractedFile).filter(ExtractedFile.package_id == package_id).all()
            if not files:
                log_package_event(package_id, "PIPELINE", "No files found for package", level="WARNING", new_status="FAILED")
                return

            # 2. Document conversion & Context aggregation
            log_package_event(package_id, "PIPELINE", f"Preparing document for classification (found {len(files)} files)")
            email_body = ""
            main_document_file = None
            
            # Supported primary document types
            visual_mimes = ["application/pdf", "image/png", "image/jpeg", "image/webp"]
            textual_mimes = ["text/plain", "text/html", "text/csv"]

            for f in files:
                if f.mime_type in textual_mimes:
                    text_content = f.extracted_text or (f.content.decode('utf-8', errors='ignore') if f.content else "")
                    email_body += text_content + "\n"
                    # Use text file as fallback if no processable doc found yet
                    if not main_document_file:
                        main_document_file = f
                elif f.mime_type in visual_mimes:
                    # Prefer PDF/Image over text
                    if not main_document_file or main_document_file.mime_type in textual_mimes:
                        main_document_file = f
            
            if not main_document_file:
                log_package_event(package_id, "PIPELINE", "No processable document found in package", level="ERROR", new_status="FAILED")
                return

            log_package_event(package_id, "PIPELINE", f"Selected '{main_document_file.filename}' as primary document")

            # Prepare items for extraction
            items_to_process = []
            if main_document_file.mime_type == "application/pdf":
                log_package_event(package_id, "PIPELINE", "Converting PDF to images for processing")
                try:
                    pdf_pages = convert_from_bytes(main_document_file.content)
                    for i, page in enumerate(pdf_pages):
                        img_byte_arr = io.BytesIO()
                        page.save(img_byte_arr, format='PNG')
                        items_to_process.append({
                            "content": img_byte_arr.getvalue(),
                            "mime_type": "image/png",
                            "width": page.width,
                            "height": page.height,
                            "file_id": main_document_file.id,
                            "page_num": i + 1
                        })
                    log_package_event(package_id, "PIPELINE", f"Converted PDF to {len(items_to_process)} pages")
                except Exception as e:
                    log_package_event(package_id, "PIPELINE", f"PDF conversion failed: {str(e)}", level="ERROR")
                    raise
            elif main_document_file.mime_type in ["image/png", "image/jpeg", "image/webp"]:
                try:
                    img = Image.open(io.BytesIO(main_document_file.content))
                    items_to_process.append({
                        "content": main_document_file.content,
                        "mime_type": main_document_file.mime_type,
                        "width": img.width,
                        "height": img.height,
                        "file_id": main_document_file.id,
                        "page_num": 1
                    })
                    if not main_document_file.width or not main_document_file.height:
                        main_document_file.width = img.width
                        main_document_file.height = img.height
                except Exception as e:
                    log_package_event(package_id, "PIPELINE", f"Image loading failed: {str(e)}", level="ERROR")
                    raise
            else:
                # Handle text-only (txt, csv, html)
                content = main_document_file.extracted_text.encode() if main_document_file.extracted_text else main_document_file.content
                items_to_process.append({
                    "content": content,
                    "mime_type": main_document_file.mime_type,
                    "width": 0,
                    "height": 0,
                    "file_id": main_document_file.id,
                    "page_num": 1
                })

            # 3. Classification
            log_package_event(package_id, "CLASSIFICATION", "Starting document classification", new_status="CLASSIFYING")
            first_item = items_to_process[0]
            doc_type = self.classification_service.classify(
                content=first_item["content"],
                mime_type=first_item["mime_type"]
            )
            
            if doc_type == "UNKNOWN":
                log_package_event(package_id, "CLASSIFICATION", "Document type UNKNOWN", level="WARNING", new_status="FAILED")
                return

            log_package_event(package_id, "CLASSIFICATION", f"Document classified as '{doc_type}'", level="SUCCESS")

            # 4. Extraction
            log_package_event(package_id, "EXTRACTION", f"Starting extraction for type '{doc_type}'", new_status="EXTRACTING")
            schema = self._load_schema(doc_type)
            if not schema:
                log_package_event(package_id, "EXTRACTION", f"No extraction schema found for type {doc_type}", level="ERROR", new_status="FAILED")
                return

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
                
                # 5. Post-processing: Scale BBoxes (only if it was an image)
                result_dict = {name: triplet.dict() for name, triplet in result.fields.items()}
                if item_data["width"] > 0 and item_data["height"] > 0:
                    scaled_result_dict = self._scale_triplet_bboxes(
                        result_dict, 
                        item_data["width"], 
                        item_data["height"]
                    )
                else:
                    scaled_result_dict = result_dict
                
                # Calculate aggregate confidence
                confidences = [t["confidence"] for t in scaled_result_dict.values() if isinstance(t, dict) and "confidence" in t]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

                # 6. Persistence
                extraction_record = Extractions(
                    package_id=package_id,
                    file_id=item_data["file_id"],
                    document_type=doc_type,
                    extraction_json=json.dumps(scaled_result_dict),
                    confidence_score=avg_confidence
                )
                session.add(extraction_record)
                all_results.append(scaled_result_dict)

            # Update package status
            session.commit()
            log_package_event(package_id, "EXTRACTION", "Extraction completed successfully", level="SUCCESS", new_status="EXTRACTED")
            log_package_event(package_id, "PIPELINE", "Pipeline completed successfully", level="SUCCESS")

        except Exception as e:
            log_package_event(package_id, "PIPELINE", f"Pipeline failed: {str(e)}", level="ERROR", new_status="FAILED")
            session.rollback()

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
