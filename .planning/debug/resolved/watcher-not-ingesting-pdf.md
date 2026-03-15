---
status: investigating
trigger: "watcher-not-ingesting-pdf"
created: 2025-03-05T10:30:00Z
updated: 2025-03-05T10:30:00Z
---

## Current Focus

hypothesis: The watcher might be ignoring the file due to its extension, or it's already in the "processed" or "failed" database but still in the folder, or the watcher is hung.
test: Check watcher configuration and current state of the ingest folder and database.
expecting: Identify why the file is being skipped.
next_action: Examine src/services/watcher.py and src/services/ingestor.py.

## Symptoms

expected: The file (.pdf) is processed by the watcher and moves out of `ingest/`.
actual: The file just sits there in `ingest/` without being ingested.
errors: None in the terminal or UI logs.
reproduction: Place a .pdf file in the ingest folder.
started: The file watcher has successfully processed files before, but is not picking up this .pdf.

## Eliminated

## Evidence

## Resolution

root_cause: 
fix: 
verification: 
files_changed: []
