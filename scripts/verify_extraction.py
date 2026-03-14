import os
import sys
import json
import argparse
import logging
import asyncio
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.session import db_session, init_db
from src.services.ingestor import RecursiveIngestor
from src.services.extraction_pipeline import ExtractionPipeline
from src.models.schema import Package, ExtractedFile, Extractions

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def format_bbox(bbox_data: Any) -> str:
    """Format bounding box for display."""
    if not bbox_data:
        return "None"
    if isinstance(bbox_data, dict) and "coordinates" in bbox_data:
        coords = bbox_data["coordinates"]
        if coords:
            return f"[{', '.join(map(str, coords))}]"
    return str(bbox_data)

def print_extraction_results(package_id: str):
    """Fetch and print extraction results for a package."""
    session = db_session()
    try:
        package = session.query(Package).filter_by(id=package_id).one()
        extractions = session.query(Extractions).filter_by(package_id=package_id).all()
        
        print(f"\n" + "="*60)
        print(f"EXTRACTION RESULTS FOR PACKAGE: {package_id}")
        print(f"Original File: {package.original_filename}")
        print(f"Final Status:  {package.status}")
        print("="*60)

        if not extractions:
            print("No extraction records found.")
            return

        total_fields = 0
        total_confidence = 0.0
        field_count = 0

        for ext in extractions:
            print(f"\nDocument Type: {ext.document_type}")
            print(f"Confidence Score: {ext.confidence_score:.4f}")
            print("-" * 40)
            
            try:
                data = json.loads(ext.extraction_json)
                for field_name, triplet in data.items():
                    val = triplet.get("value")
                    conf = triplet.get("confidence", 0.0)
                    bbox = format_bbox(triplet.get("bbox"))
                    
                    print(f"  {field_name:.<25} {str(val):.<25} (Conf: {conf:.2f}, BBox: {bbox})")
                    
                    total_confidence += conf
                    field_count += 1
            except Exception as e:
                print(f"Error parsing extraction JSON: {e}")

        if field_count > 0:
            avg_conf = total_confidence / field_count
            print("\n" + "-"*40)
            print(f"SUMMARY:")
            print(f"Total Fields Extracted: {field_count}")
            print(f"Average Confidence:     {avg_conf:.4f}")
            print("-" * 40)

    finally:
        session.close()

async def run_verification(file_path: Optional[str] = None):
    init_db()
    session = db_session()
    
    package_id = None
    
    try:
        if file_path:
            if not os.path.exists(file_path):
                print(f"Error: File not found at {file_path}")
                return
            
            print(f"--- Step 1: Ingesting {os.path.basename(file_path)} ---")
            ingestor = RecursiveIngestor()
            package_id = ingestor.process_package(session, file_path, os.path.basename(file_path))
            print(f"Package ID: {package_id}")
        else:
            # Look for latest INGESTED package
            package = session.query(Package).filter_by(status="INGESTED").order_by(Package.created_at.desc()).first()
            if package:
                package_id = package.id
                print(f"Using latest INGESTED package: {package_id}")
            else:
                print("No INGESTED packages found and no file provided.")
                # Try to ingest default test file if exists
                for default_file in ["test_sample.zip", "test.eml"]:
                    if os.path.exists(default_file):
                        print(f"Found default test file: {default_file}. Ingesting...")
                        ingestor = RecursiveIngestor()
                        package_id = ingestor.process_package(session, default_file, default_file)
                        print(f"Package ID: {package_id}")
                        break
                
                if not package_id:
                    print("Error: Could not find any package to process.")
                    return

        print(f"\n--- Step 2: Running Extraction Pipeline ---")
        pipeline = ExtractionPipeline()
        # We run it synchronously for verification
        pipeline.process_package(package_id)
        
        # Step 3: Print Results
        print_extraction_results(package_id)

    except Exception as e:
        logger.exception(f"Verification failed: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify full extraction flow.")
    parser.add_argument("--file", help="Path to a new file to ingest and extract.")
    
    args = parser.parse_args()
    asyncio.run(run_verification(args.file))
