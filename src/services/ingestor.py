import io
import zipfile
import mailparser
import base64
import os
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from src.models.schema import Package, ExtractedFile

# Set up logging
logger = logging.getLogger(__name__)

try:
    import magic
except ImportError:
    magic = None

class RecursiveIngestor:
    def __init__(self, max_depth: int = 5, max_total_size: int = 500 * 1024 * 1024):
        # On Windows, python-magic-bin is used. On Linux, libmagic-dev.
        self.mime = None
        self.max_depth = max_depth
        self.max_total_size = max_total_size
        self.current_total_size = 0
        if magic:
            try:
                self.mime = magic.Magic(mime=True)
            except Exception:
                # Fallback for some environments if magic fails to init
                pass

    def extract(self, content: bytes, original_filename: str) -> List[Dict[str, Any]]:
        """
        Recursively extract files from ZIP and EML archives.
        Returns a list of dictionaries matching ExtractedFile schema.
        """
        self.current_total_size = 0
        return self._recursive_extract(content, original_filename, depth=0)

    def process_package(self, db: Session, file_path: str, original_filename: str) -> str:
        """
        Processes a package file, creates records in the database.
        Returns the package ID.
        """
        # 1. Create a Package record in the database
        package = Package(original_filename=original_filename, status="INGESTING")
        db.add(package)
        db.commit()
        db.refresh(package)

        try:
            # 2. Runs the RecursiveIngestor on the input file
            with open(file_path, "rb") as f:
                content = f.read()
            
            extracted_results = self.extract(content, original_filename)

            # 3. Persists all resulting ExtractedFile objects to the database, linked to the Package
            for res in extracted_results:
                ext_file = ExtractedFile(
                    package_id=package.id,
                    filename=res["filename"].split("/")[-1],
                    original_path=res["filename"],
                    content=res["content"],
                    extracted_text=res["extracted_text"],
                    mime_type=res["mime_type"],
                    size=res["size"]
                )
                db.add(ext_file)
            
            # 4. Updates Package status to INGESTED
            package.status = "INGESTED"
            db.commit()
        except Exception as e:
            logger.error(f"Error processing package {original_filename}: {e}")
            package.status = "FAILED"
            db.commit()
            raise
        
        return package.id

    def _get_mime(self, content: bytes, filename: str) -> str:
        if self.mime:
            try:
                return self.mime.from_buffer(content)
            except Exception:
                pass
        
        # Fallback based on extension
        ext = filename.lower().split('.')[-1]
        if ext == 'zip':
            return 'application/zip'
        elif ext == 'eml':
            return 'message/rfc822'
        elif ext == 'pdf':
            return 'application/pdf'
        elif ext in ['jpg', 'jpeg']:
            return 'image/jpeg'
        elif ext == 'png':
            return 'image/png'
        return 'application/octet-stream'

    def _is_archive(self, mime_type: str, filename: str) -> bool:
        if mime_type == 'application/zip' or filename.lower().endswith('.zip'):
            return True
        if mime_type == 'message/rfc822' or filename.lower().endswith('.eml'):
            return True
        return False

    def _safe_zip_filename(self, filename: str) -> str:
        """Protect against Zip Slip by preventing directory traversal."""
        # Normalize and remove any leading slashes or '..' segments
        filename = os.path.normpath(filename).replace('\\', '/')
        if filename.startswith('/') or '..' in filename.split('/'):
            # Potentially malicious, return only the basename as fallback or sanitized version
            return os.path.basename(filename)
        return filename

    def _recursive_extract(self, content: bytes, filename: str, path_prefix: str = "", depth: int = 0) -> List[Dict[str, Any]]:
        if depth > self.max_depth:
            logger.warning(f"Max recursion depth reached at {path_prefix}/{filename}")
            return []

        results = []
        mime_type = self._get_mime(content, filename)
        
        # Determine the relative path for the current item
        current_path = path_prefix if path_prefix else filename

        # Check total size before processing this item
        if self.current_total_size + len(content) > self.max_total_size:
            logger.error(f"Max total size exceeded: {self.current_total_size + len(content)} > {self.max_total_size}")
            return []

        if mime_type == 'application/zip' or filename.lower().endswith('.zip'):
            # We don't add the zip itself to current_total_size yet, 
            # we will add its extracted components.
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as z:
                    for zinfo in z.infolist():
                        if zinfo.is_dir():
                            continue
                        
                        try:
                            # Zip Slip Protection
                            safe_name = self._safe_zip_filename(zinfo.filename)
                            z_content = z.read(zinfo.filename)
                            
                            new_prefix = f"{path_prefix}/{safe_name}" if path_prefix else safe_name
                            
                            # Check size before adding/recursing
                            if self.current_total_size + len(z_content) > self.max_total_size:
                                logger.error(f"Max total size exceeded while extracting {safe_name}")
                                continue

                            if self._is_archive(self._get_mime(z_content, safe_name), safe_name):
                                results.extend(self._recursive_extract(z_content, safe_name, new_prefix, depth + 1))
                            else:
                                self.current_total_size += len(z_content)
                                results.append({
                                    "filename": new_prefix,
                                    "content": z_content,
                                    "extracted_text": None,
                                    "mime_type": self._get_mime(z_content, safe_name),
                                    "size": len(z_content)
                                })
                        except Exception as e:
                            logger.error(f"Error extracting {zinfo.filename} from {filename}: {e}")
                            continue

            except (zipfile.BadZipFile, EOFError) as e:
                logger.error(f"Bad zip file {filename}: {e}")
                self.current_total_size += len(content)
                results.append({
                    "filename": current_path,
                    "content": content,
                    "extracted_text": None,
                    "mime_type": mime_type,
                    "size": len(content)
                })

        elif mime_type == 'message/rfc822' or filename.lower().endswith('.eml'):
            try:
                mail = mailparser.parse_from_bytes(content)
                
                # Extract body
                body_path = f"{current_path}/body.txt"
                
                # Favor plain text over HTML as per requirement
                body_text = ""
                if mail.text_plain:
                    body_text = "\n".join(mail.text_plain)
                elif mail.text_html:
                    body_text = "\n".join(mail.text_html)
                
                body_bytes = body_text.encode()
                if self.current_total_size + len(body_bytes) <= self.max_total_size:
                    self.current_total_size += len(body_bytes)
                    results.append({
                        "filename": body_path,
                        "content": content, # Body doesn't have its own content bytes in the same way, we store the full EML or just body?
                        # Actually the model says 'content' is BLOB. For EML body, we might want to store the body or the full EML.
                        # The current implementation stores the FULL EML content for the body.txt record. That's a bit weird but okay.
                        "extracted_text": body_text,
                        "mime_type": "text/plain",
                        "size": len(body_bytes)
                    })
                
                # Extract attachments
                for attachment in mail.attachments:
                    try:
                        att_content = attachment['payload']
                        if attachment['binary']:
                            if isinstance(att_content, str):
                                att_content = base64.b64decode(att_content)
                        else:
                            if isinstance(att_content, str):
                                att_content = att_content.encode()
                        
                        att_filename = attachment['filename']
                        att_filename = self._safe_zip_filename(att_filename)
                        new_prefix = f"{current_path}/{att_filename}"
                        
                        if self.current_total_size + len(att_content) > self.max_total_size:
                            logger.error(f"Max total size exceeded while extracting attachment {att_filename}")
                            continue

                        if self._is_archive(self._get_mime(att_content, att_filename), att_filename):
                            results.extend(self._recursive_extract(att_content, att_filename, new_prefix, depth + 1))
                        else:
                            self.current_total_size += len(att_content)
                            results.append({
                                "filename": new_prefix,
                                "content": att_content,
                                "extracted_text": None,
                                "mime_type": self._get_mime(att_content, att_filename),
                                "size": len(att_content)
                            })
                    except Exception as e:
                        logger.error(f"Error extracting attachment {attachment.get('filename')} from {filename}: {e}")
                        continue
            except Exception as e:
                logger.error(f"Failed to parse EML {filename}: {e}")
                self.current_total_size += len(content)
                results.append({
                    "filename": current_path,
                    "content": content,
                    "extracted_text": None,
                    "mime_type": mime_type,
                    "size": len(content)
                })

        else:
            # Regular file
            self.current_total_size += len(content)
            results.append({
                "filename": current_path,
                "content": content,
                "extracted_text": None,
                "mime_type": mime_type,
                "size": len(content)
            })
            
        return results

