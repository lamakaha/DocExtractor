import asyncio
import argparse
import logging
from src.db.session import init_db, db_session
from src.models.schema import Package
from src.services.extraction_pipeline import ExtractionPipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def process_pending_packages(max_workers: int = 5):
    """
    Finds all packages with INGESTED status and processes them.
    """
    session = db_session()
    pending_packages = session.query(Package).filter(Package.status == "INGESTED").all()
    
    if not pending_packages:
        logger.info("No pending packages found.")
        return

    package_ids = [p.id for p in pending_packages]
    logger.info(f"Found {len(package_ids)} pending packages. Starting extraction...")

    pipeline = ExtractionPipeline()
    await pipeline.process_packages_parallel(package_ids, max_workers=max_workers)
    
    logger.info("Batch processing complete.")

def main():
    parser = argparse.ArgumentParser(description="DocExtractor CLI")
    parser.add_index = parser.add_subparsers(dest="command", help="Commands")
    
    # Process command
    process_parser = parser.add_index.add_parser("process", help="Process pending packages")
    process_parser.add_argument("--workers", type=int, default=5, help="Number of concurrent workers")

    # Init DB command
    parser.add_index.add_parser("init-db", help="Initialize the database")

    args = parser.parse_args()

    if args.command == "init-db":
        init_db()
        print("Database initialized.")
    elif args.command == "process":
        init_db()
        asyncio.run(process_pending_packages(max_workers=args.workers))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
