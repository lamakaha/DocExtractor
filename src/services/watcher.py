import os
import time
import shutil
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from src.db.session import db_session
from src.services.ingestor import RecursiveIngestor
from src.services.extraction_pipeline import ExtractionPipeline

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IngestionHandler(FileSystemEventHandler):
    """
    Handles file system events in the ingest directory.
    """
    def __init__(self, processed_dir: str, failed_dir: str):
        self.processed_dir = processed_dir
        self.failed_dir = failed_dir
        self.ingestor = RecursiveIngestor()
        self.pipeline = ExtractionPipeline()

    def on_created(self, event):
        if not event.is_directory:
            self._process_new_file(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self._process_new_file(event.dest_path)

    def _process_new_file(self, file_path: str):
        filename = os.path.basename(file_path)
        
        # Avoid processing files already in subdirectories
        if self.processed_dir in file_path or self.failed_dir in file_path:
            return

        # Filter for supported extensions
        ext = filename.lower().split('.')[-1]
        if ext not in ['zip', 'eml', 'pdf', 'png', 'jpg', 'jpeg']:
            logger.info(f"Ignoring file with unsupported extension: {filename}")
            return

        logger.info(f"New file detected: {filename}. Starting pipeline...")
        
        # Wait a brief moment to ensure file is fully written (especially for large files)
        time.sleep(1)

        session = db_session()
        try:
            # 1. Ingestion
            package_id = self.ingestor.process_package(session, file_path, filename)
            logger.info(f"Ingested {filename} -> Package ID: {package_id}")

            # 2. Extraction
            # process_package in pipeline manages its own session
            self.pipeline.process_package(package_id)
            logger.info(f"Extraction complete for Package ID: {package_id}")

            # 3. Move to processed
            dest_path = os.path.join(self.processed_dir, filename)
            # Handle filename collisions in processed dir
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(filename)
                dest_path = os.path.join(self.processed_dir, f"{base}_{int(time.time())}{ext}")
            
            shutil.move(file_path, dest_path)
            logger.info(f"Moved {filename} to {self.processed_dir}")

        except Exception as e:
            logger.error(f"Failed to process {filename}: {str(e)}")
            # Move to failed
            dest_path = os.path.join(self.failed_dir, filename)
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(filename)
                dest_path = os.path.join(self.failed_dir, f"{base}_{int(time.time())}{ext}")
            
            try:
                shutil.move(file_path, dest_path)
                logger.info(f"Moved {filename} to {self.failed_dir}")
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
        logger.info(f"Starting file watcher on: {self.watch_dir}")
        self.observer.schedule(self.handler, self.watch_dir, recursive=False)
        self.observer.start()
        if blocking:
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.stop()

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
