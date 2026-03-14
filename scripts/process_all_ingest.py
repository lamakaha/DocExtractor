import os
import sys
import asyncio
import logging
import shutil
import time

# Add project root to path
sys.path.append(os.path.abspath("."))

from src.db.session import db_session, init_db
from src.services.ingestor import RecursiveIngestor
from src.services.extraction_pipeline import ExtractionPipeline
from src.models.schema import Package

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def process_all():
    init_db()
    
    ingest_dir = "ingest"
    processed_dir = os.path.join(ingest_dir, "processed")
    failed_dir = os.path.join(ingest_dir, "failed")
    
    os.makedirs(processed_dir, exist_ok=True)
    os.makedirs(failed_dir, exist_ok=True)
    
    ingestor = RecursiveIngestor()
    pipeline = ExtractionPipeline()
    
    # Recursively find all files in ingest_dir, excluding processed and failed dirs
    files_to_process = []
    for root, dirs, files in os.walk(ingest_dir):
        # Skip processed and failed directories
        if "processed" in root or "failed" in root:
            continue
            
        for f in files:
            file_path = os.path.join(root, f)
            files_to_process.append((file_path, f))
    
    logger.info(f"Found {len(files_to_process)} files to process.")
    
    for file_path, filename in files_to_process:
        # Re-open session for each package to avoid transaction issues
        session = db_session()
        logger.info(f"Processing {file_path}...")
        
        try:
            # 1. Ingestion
            package_id = ingestor.process_package(session, file_path, filename)
            logger.info(f"Ingested {filename} -> Package ID: {package_id}")
            
            # 2. Extraction
            pipeline.process_package(package_id)
            logger.info(f"Extraction complete for Package ID: {package_id}")
            
            # Check if successful
            session.expire_all()
            pkg = session.query(Package).filter_by(id=package_id).one()
            
            if pkg.status == "EXTRACTED":
                dest_path = os.path.join(processed_dir, filename)
                # Handle filename collision
                if os.path.exists(dest_path):
                    base, ext = os.path.splitext(filename)
                    dest_path = os.path.join(processed_dir, f"{base}_{int(time.time())}{ext}")
                shutil.move(file_path, dest_path)
                logger.info(f"Moved {file_path} to {dest_path}")
            else:
                logger.error(f"Extraction failed for {filename} (Status: {pkg.status})")
                dest_path = os.path.join(failed_dir, filename)
                # Handle filename collision
                if os.path.exists(dest_path):
                    base, ext = os.path.splitext(filename)
                    dest_path = os.path.join(failed_dir, f"{base}_{int(time.time())}{ext}")
                shutil.move(file_path, dest_path)
                logger.info(f"Moved {file_path} to {dest_path}")
                
        except Exception as e:
            logger.exception(f"Error processing {filename}: {e}")
            try:
                dest_path = os.path.join(failed_dir, filename)
                shutil.move(file_path, dest_path)
            except:
                pass
        finally:
            session.close()
        
        # Wait to avoid rate limits
        logger.info("Sleeping for 5 seconds to avoid rate limits...")
        await asyncio.sleep(5)

    logger.info("Bulk processing complete.")

if __name__ == "__main__":
    asyncio.run(process_all())
