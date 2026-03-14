import os
import sys
import argparse
import logging
from typing import List, Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.session import db_session, init_db
from src.services.ingestor import RecursiveIngestor
from src.models.schema import Package, ExtractedFile

# Set up logging to display errors but keep output clean
logging.basicConfig(level=logging.ERROR)

def build_tree(paths: List[str]) -> Dict[str, Any]:
    tree = {}
    for path in paths:
        parts = path.split('/')
        current = tree
        for part in parts:
            if part not in current:
                current[part] = {}
            current = current[part]
    return tree

def print_tree(tree: Dict[str, Any], indent: str = ""):
    keys = sorted(tree.keys())
    for i, key in enumerate(keys):
        is_last = (i == len(keys) - 1)
        prefix = "└── " if is_last else "├── "
        child_indent = "    " if is_last else "│   "
        
        print(f"{indent}{prefix}{key}")
        print_tree(tree[key], indent + child_indent)

def verify_file(file_path: str):
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    print(f"--- Ingesting: {os.path.basename(file_path)} ---")
    
    init_db()
    session = db_session()
    
    ingestor = RecursiveIngestor()
    
    try:
        package_id = ingestor.process_package(session, file_path, os.path.basename(file_path))
        print(f"Package ID: {package_id}")
        
        package = session.query(Package).filter_by(id=package_id).one()
        extracted_files = session.query(ExtractedFile).filter_by(package_id=package_id).all()
        
        print(f"Status: {package.status}")
        print(f"Total files extracted: {len(extracted_files)}")
        print("\nExtracted File Tree:")
        
        paths = [f.original_path for f in extracted_files]
        tree = build_tree(paths)
        print_tree(tree)
        
        print("\n--- Details & Previews ---")
        for f in extracted_files:
            print(f"\n[ {f.original_path} ]")
            print(f"  MIME: {f.mime_type}")
            print(f"  Size: {f.size} bytes")
            if f.extracted_text:
                preview = f.extracted_text[:200].replace('\n', ' ')
                if len(f.extracted_text) > 200:
                    preview += "..."
                print(f"  Text Preview: {preview}")
        
        print("\nVerification Complete.")

    except Exception as e:
        print(f"ERROR during ingestion: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify ingestion pipeline for a given archive file.")
    parser.add_argument("file", help="Path to the archive file (.eml, .zip, etc.)")
    
    args = parser.parse_args()
    verify_file(args.file)
