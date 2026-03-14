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

        try:
            logger.info(f"Processing package {package_id} ({package.original_filename})")
            
            # 1. Fetch extracted files
            files = session.query(ExtractedFile).filter(ExtractedFile.package_id == package_id).all()
            if not files:
                logger.warning(f"No files found for package {package_id}")
                package.status = "FAILED"
                session.commit()
                return

            # 2. Document conversion & Context aggregation
            # We look for the "main" document for classification.
            # Usually a PDF or an Image. Email body can provide context.
            email_body = ""
            main_document_file = None
            
            for f in files:
                if f.mime_type in ["text/plain", "text/html"]:
                    email_body += (f.extracted_text or "") + "\n"
                elif f.mime_type in ["application/pdf", "image/png", "image/jpeg", "image/webp"]:
                    if not main_document_file:
                        main_document_file = f
            
            if not main_document_file:
                logger.warning(f"No processable document found in package {package_id}")
                package.status = "FAILED"
                session.commit()
                return

            # Prepare images for extraction
            # Each entry: (image_bytes, mime_type, width, height, source_file_id)
            images_to_process = []

            if main_document_file.mime_type == "application/pdf":
                # Convert PDF to images
                # Note: This might be memory intensive for large PDFs
                try:
                    pdf_pages = convert_from_bytes(main_document_file.content)
                    for i, page in enumerate(pdf_pages):
                        img_byte_arr = io.BytesIO()
                        page.save(img_byte_arr, format='PNG')
                        images_to_process.append({
                            "content": img_byte_arr.getvalue(),
                            "mime_type": "image/png",
                            "width": page.width,
                            "height": page.height,
                            "file_id": main_document_file.id,
                            "page_num": i + 1
                        })
                except Exception as e:
                    logger.error(f"Failed to convert PDF to images: {e}")
                    raise
            else:
                # Handle image
                try:
                    img = Image.open(io.BytesIO(main_document_file.content))
                    images_to_process.append({
                        "content": main_document_file.content,
                        "mime_type": main_document_file.mime_type,
                        "width": img.width,
                        "height": img.height,
                        "file_id": main_document_file.id,
                        "page_num": 1
                    })
                    # Update dimensions in DB if missing
                    if not main_document_file.width or not main_document_file.height:
                        main_document_file.width = img.width
                        main_document_file.height = img.height
                except Exception as e:
                    logger.error(f"Failed to load image: {e}")
                    raise

            # 3. Classification
            # Use the first page/image for classification
            first_image = images_to_process[0]
            doc_type = self.classification_service.classify(
                content=first_image["content"],
                mime_type=first_image["mime_type"]
            )
            
            if doc_type == "UNKNOWN":
                logger.warning(f"Document type UNKNOWN for package {package_id}")
                # We still try to extract if we can find a default schema? 
                # For now, mark as FAILED or handle as UNKNOWN.
                # Actually, if we don't have a schema, we can't extract.
                package.status = "FAILED"
                session.commit()
                return

            logger.info(f"Classified package {package_id} as {doc_type}")

            # 4. Extraction
            schema = self._load_schema(doc_type)
            if not schema:
                logger.error(f"No extraction schema found for type {doc_type}")
                package.status = "FAILED"
                session.commit()
                return

            all_results = []
            for img_data in images_to_process:
                result = self.extraction_service.extract(
                    content=img_data["content"],
                    mime_type=img_data["mime_type"],
                    doc_type=doc_type,
                    extraction_schema=schema
                )
                
                # 5. Post-processing: Scale BBoxes
                # ExtractionResult.fields is dict[str, Triplet]
                # We convert to dict and scale
                result_dict = {name: triplet.dict() for name, triplet in result.fields.items()}
                scaled_result_dict = self._scale_triplet_bboxes(
                    result_dict, 
                    img_data["width"], 
                    img_data["height"]
                )
                
                # Calculate aggregate confidence
                confidences = [t["confidence"] for t in scaled_result_dict.values() if isinstance(t, dict) and "confidence" in t]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

                # 6. Persistence
                extraction_record = Extractions(
                    package_id=package_id,
                    file_id=img_data["file_id"],
                    document_type=doc_type,
                    extraction_json=json.dumps(scaled_result_dict),
                    confidence_score=avg_confidence
                )
                session.add(extraction_record)
                all_results.append(scaled_result_dict)

            # Update package status
            package.status = "EXTRACTED"
            session.commit()
            logger.info(f"Successfully processed package {package_id}")

        except Exception as e:
            logger.exception(f"Error processing package {package_id}: {e}")
            package.status = "FAILED"
            session.commit()

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
