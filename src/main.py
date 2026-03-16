import asyncio
import argparse
import logging
import uuid
from src.db.session import init_db, db_session
from src.services.extraction_pipeline import ExtractionPipeline
from src.services.extraction_job_service import ExtractionJobService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def process_pending_packages(max_workers: int = 5):
    """
    Claims queued extraction jobs and processes them.
    """
    pipeline = ExtractionPipeline()
    job_service = ExtractionJobService()
    worker_prefix = f"cli-{uuid.uuid4()}"

    async def worker(worker_num: int):
        processed = 0
        worker_id = f"{worker_prefix}-{worker_num}"
        while True:
            session = db_session()
            try:
                job = job_service.claim_next_job(session, worker_id)
            finally:
                session.close()

            if not job:
                return processed

            success = await asyncio.to_thread(pipeline.process_package, job.package_id)

            session = db_session()
            try:
                if success:
                    job_service.complete_job(session, job.id)
                else:
                    job_service.fail_job(session, job.id, "Extraction pipeline returned failure")
            finally:
                session.close()
            processed += 1

    results = await asyncio.gather(*(worker(i + 1) for i in range(max_workers)))
    total_processed = sum(results)
    if total_processed == 0:
        logger.info("No queued extraction jobs found.")
        return
    logger.info(f"Batch processing complete. Processed {total_processed} job(s).")

def main():
    parser = argparse.ArgumentParser(description="DocExtractor CLI")
    parser.add_index = parser.add_subparsers(dest="command", help="Commands")
    
    # Process command
    process_parser = parser.add_index.add_parser("process", help="Process pending packages")
    process_parser.add_argument("--workers", type=int, default=5, help="Number of concurrent workers")

    # Watch command
    parser.add_index.add_parser("watch", help="Watch 'ingest' directory for new files")

    # Init DB command
    parser.add_index.add_parser("init-db", help="Initialize the database")

    args = parser.parse_args()

    if args.command == "init-db":
        init_db()
        print("Database initialized.")
    elif args.command == "process":
        init_db()
        asyncio.run(process_pending_packages(max_workers=args.workers))
    elif args.command == "watch":
        init_db()
        from src.services.watcher import FileWatcher
        watcher = FileWatcher()
        watcher.start()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
