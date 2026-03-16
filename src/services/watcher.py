import os
import time
import shutil
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from src.db.session import db_session
from src.services.ingestor import RecursiveIngestor
from src.services.extraction_job_service import ExtractionJobService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IngestionHandler(FileSystemEventHandler):
    """
    Handles file system events in the ingest directory.
    """
    def __init__(self, processed_dir: str, failed_dir: str):
        self.processed_dir = Path(processed_dir).resolve()
        self.failed_dir = Path(failed_dir).resolve()
        self.ingestor = RecursiveIngestor()
        self.job_service = ExtractionJobService()

    def on_created(self, event):
        if not event.is_directory:
            self._process_new_file(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self._process_new_file(event.dest_path)

    def _process_new_file(self, file_path: str):
        path = Path(file_path).resolve()
        filename = path.name
        
        # Avoid processing files strictly inside system subdirectories (processed/failed)
        # Using .parents or checking if the path starts with the base dir
        if self.processed_dir in path.parents or path.parent == self.processed_dir:
            return
        if self.failed_dir in path.parents or path.parent == self.failed_dir:
            return

        # Filter for supported extensions
        ext = filename.lower().split('.')[-1]
        if ext not in ['zip', 'eml', 'pdf', 'png', 'jpg', 'jpeg', 'txt', 'csv']:
            logger.info(f"Ignoring file with unsupported extension: {filename}")
            return

        logger.info(f"New file detected: {file_path}. Starting ingestion...")
        
        # Wait a brief moment to ensure file is fully written (especially for large files)
        time.sleep(1)

        session = db_session()
        try:
            # 1. Ingestion
            package_id = self.ingestor.process_package(session, str(path), filename)
            logger.info(f"Ingested {filename} -> Package ID: {package_id}")

            # 2. Queue extraction
            job = self.job_service.enqueue_package(session, package_id)
            logger.info(f"Queued extraction job {job.id} for Package ID: {package_id}")

            # 3. Move to processed
            dest_path = self.processed_dir / filename
            # Handle filename collisions in processed dir
            if dest_path.exists():
                base = dest_path.stem
                ext_orig = dest_path.suffix
                dest_path = self.processed_dir / f"{base}_{int(time.time())}{ext_orig}"
            
            shutil.move(str(path), str(dest_path))
            logger.info(f"Moved {file_path} to {dest_path}")

        except Exception as e:
            logger.error(f"Failed to process {filename}: {str(e)}")
            # Move to failed
            dest_path = self.failed_dir / filename
            if dest_path.exists():
                base = dest_path.stem
                ext_orig = dest_path.suffix
                dest_path = self.failed_dir / f"{base}_{int(time.time())}{ext_orig}"
            
            try:
                shutil.move(str(path), str(dest_path))
                logger.info(f"Moved {file_path} to {dest_path}")
            except Exception as move_err:
                logger.error(f"Critical: Could not move failed file {filename}: {move_err}")
        finally:
            session.close()

class FileWatcher:
    """
    Watches a directory for new files and triggers ingestion.
    """
    def __init__(self, watch_dir: str = "ingest"):
        self.watch_dir = os.path.abspath(watch_dir)
        self.processed_dir = os.path.join(self.watch_dir, "processed")
        self.failed_dir = os.path.join(self.watch_dir, "failed")
        
        # Ensure directories exist
        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs(self.failed_dir, exist_ok=True)
        
        self.observer = Observer()
        self.handler = IngestionHandler(self.processed_dir, self.failed_dir)

    def start(self, blocking: bool = True):
        logger.info(f"Starting file watcher on: {self.watch_dir} (recursive=True)")
        
        self._process_existing_files()
        
        self.observer.schedule(self.handler, self.watch_dir, recursive=True)
        self.observer.start()
        if blocking:
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.stop()

    def _process_existing_files(self):
        logger.info(f"Scanning for existing files in {self.watch_dir}...")
        processed_path = Path(self.processed_dir).resolve()
        failed_path = Path(self.failed_dir).resolve()
        
        for root, dirs, files in os.walk(self.watch_dir):
            root_path = Path(root).resolve()
            
            # Prevent walking into processed or failed directories
            if root_path == processed_path or root_path == failed_path:
                continue
                
            # Modify dirs in-place to avoid descending into them
            if 'processed' in dirs:
                dirs.remove('processed')
            if 'failed' in dirs:
                dirs.remove('failed')
                
            for file in files:
                file_path = os.path.join(root, file)
                self.handler._process_new_file(file_path)

    @property
    def is_running(self) -> bool:
        return self.observer.is_alive()

    def stop(self):
        if self.is_running:
            logger.info("Stopping file watcher...")
            self.observer.stop()
            self.observer.join()
            # Observer cannot be restarted once stopped, so we create a new one for next start
            self.observer = Observer()
