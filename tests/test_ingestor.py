import pytest
import io
import zipfile
import os
import tempfile
from email.message import EmailMessage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.services.ingestor import RecursiveIngestor
from src.models.schema import Base, Package, ExtractedFile

def create_test_zip(files_dict):
    """files_dict: {filename: content}"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename, content in files_dict.items():
            zip_file.writestr(filename, content)
    return zip_buffer.getvalue()

def create_test_eml(body, attachments=None):
    """attachments: {filename: content}"""
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = 'Test Email'
    msg['From'] = 'sender@example.com'
    msg['To'] = 'receiver@example.com'
    if attachments:
        for filename, content in attachments.items():
            # For simplicity, treat as application/octet-stream
            msg.add_attachment(content, maintype='application', subtype='octet-stream', filename=filename)
    return msg.as_bytes()

def test_recursive_zip():
    # ZIP -> PDF, ZIP -> Image
    inner_zip = create_test_zip({"image.png": b"fake_image"})
    outer_zip = create_test_zip({
        "document.pdf": b"fake_pdf",
        "nested.zip": inner_zip
    })
    
    ingestor = RecursiveIngestor()
    extracted = ingestor.extract(outer_zip, "outer.zip")
    
    # Expected: document.pdf, nested.zip/image.png
    filenames = [f['filename'] for f in extracted]
    assert "document.pdf" in filenames
    assert "nested.zip/image.png" in filenames
    assert len(extracted) == 2

def test_recursive_eml():
    # EML with ZIP attachment
    inner_zip = create_test_zip({"doc.pdf": b"fake_pdf"})
    eml_content = create_test_eml("Hello body", {"archive.zip": inner_zip})
    
    ingestor = RecursiveIngestor()
    extracted = ingestor.extract(eml_content, "email.eml")
    
    # Expected: body.txt, archive.zip/doc.pdf
    filenames = [f['filename'] for f in extracted]
    assert "email.eml/body.txt" in filenames
    assert "email.eml/archive.zip/doc.pdf" in filenames
    
    body_file = next(f for f in extracted if "body.txt" in f['filename'])
    assert "Hello body" in body_file['extracted_text']

def test_deeply_nested():
    # ZIP -> EML -> ZIP -> PDF
    inner_most_zip = create_test_zip({"final.pdf": b"data"})
    eml = create_test_eml("Email body", {"inner.zip": inner_most_zip})
    outer_zip = create_test_zip({"test.eml": eml})
    
    ingestor = RecursiveIngestor()
    extracted = ingestor.extract(outer_zip, "root.zip")
    
    # Paths within root.zip:
    # test.eml
    #   test.eml/body.txt
    #   test.eml/inner.zip/final.pdf
    
    paths = [f['filename'] for f in extracted]
    assert "test.eml/body.txt" in paths
    assert "test.eml/inner.zip/final.pdf" in paths

def test_process_package():
    # Setup temporary SQLite database
    fd, temp_db_path = tempfile.mkstemp()
    os.close(fd)
    db_url = f"sqlite:///{temp_db_path}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create a test file
        test_content = create_test_zip({"file1.pdf": b"content1", "file2.txt": b"content2"})
        fd_file, temp_file_path = tempfile.mkstemp(suffix=".zip")
        with os.fdopen(fd_file, 'wb') as tmp:
            tmp.write(test_content)
        
        ingestor = RecursiveIngestor()
        package_id = ingestor.process_package(session, temp_file_path, "test_package.zip")
        
        # Verify Package
        package = session.query(Package).filter_by(id=package_id).first()
        assert package is not None
        assert package.original_filename == "test_package.zip"
        assert package.status == "INGESTED"
        
        # Verify ExtractedFiles
        extracted_files = session.query(ExtractedFile).filter_by(package_id=package_id).all()
        assert len(extracted_files) == 2
        
        filenames = [f.filename for f in extracted_files]
        assert "file1.pdf" in filenames
        assert "file2.txt" in filenames
        
        paths = [f.original_path for f in extracted_files]
        assert "file1.pdf" in paths
        assert "file2.txt" in paths

        os.remove(temp_file_path)
    finally:
        session.close()
        engine.dispose()
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)

def test_resilience():
    # 1. Max Depth
    # Create deeply nested ZIP
    inner = create_test_zip({"file.txt": b"deep"})
    for i in range(10):
        inner = create_test_zip({f"nested_{i}.zip": inner})
    
    ingestor = RecursiveIngestor(max_depth=5)
    extracted = ingestor.extract(inner, "deep.zip")
    
    # Should stop at depth 5
    # Depth 0: top level
    # Depth 1: nested_9
    # Depth 2: nested_8
    # Depth 3: nested_7
    # Depth 4: nested_6
    # Depth 5: nested_5
    # Beyond depth 5: should be empty or stopped
    
    paths = [f['filename'] for f in extracted]
    # Check if we have files from deeper than 5
    # Note: path names would be nested_9.zip/nested_8.zip/...
    assert len(paths) <= 6 # top + 5 levels (approx)
    assert not any("nested_0" in p for p in paths)

    # 2. Max Total Size
    # Create ZIP with large content
    large_content = b"x" * 1024 * 1024 # 1MB
    large_zip = create_test_zip({"large.txt": large_content})
    
    ingestor = RecursiveIngestor(max_total_size=512 * 1024) # 0.5MB limit
    extracted = ingestor.extract(large_zip, "large.zip")
    assert len(extracted) == 0

    # 3. Zip Slip Protection
    # Create ZIP with malicious filename
    slip_zip = create_test_zip({"../../etc/passwd": b"evil"})
    ingestor = RecursiveIngestor()
    extracted = ingestor.extract(slip_zip, "slip.zip")
    
    paths = [f['filename'] for f in extracted]
    assert "../../etc/passwd" not in paths
    assert "passwd" in paths # Should be sanitized to just the basename or similar
    
    # 4. Corruption Handling
    corrupt_zip = b"not a zip file at all"
    extracted = ingestor.extract(corrupt_zip, "corrupt.zip")
    # Should return the original file as a single result (as per current implementation)
    assert len(extracted) == 1
    assert extracted[0]['filename'] == "corrupt.zip"
