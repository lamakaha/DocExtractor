---
status: investigating
trigger: "watcher-not-ingesting"
created: 2025-03-03T10:00:00Z
updated: 2025-03-03T10:00:00Z
---

## Current Focus

hypothesis: The file watcher in Streamlit is not properly starting or is being blocked by Streamlit's execution model.
test: Examine `src/ui/watcher_manager.py` and `src/services/watcher.py` to see how the watcher is initialized and run.
expecting: A mismatch between how `watchdog` is used and how Streamlit handles background threads.
next_action: Examine `src/ui/watcher_manager.py` and `src/services/watcher.py`.

## Symptoms

expected: Files dropped into `ingest/` should be automatically ingested and extracted.
actual: Nothing happens when files are dropped.
errors: No output in the terminal other than Streamlit UI starting.
reproduction: Start watcher from UI, drop files in `ingest/`.
started: Always happens.

## Eliminated

## Evidence

- timestamp: 2025-03-03T10:05:00Z
  checked: src/services/classification_service.py and src/services/extraction_service.py
  found: model_id is set to "gemini-2.5-pro", which does not exist.
  implication: Classification and extraction will always fail.

- timestamp: 2025-03-03T10:06:00Z
  checked: packages.db
  found: Many packages have status FAILED.
  implication: The pipeline has been running but failing, likely due to the invalid model_id.

- timestamp: 2025-03-03T10:07:00Z
  checked: ingest/ folder contents
  found: Files are present in ingest/ but have not been moved, despite the watcher supposedly running.
  implication: The watcher might not be triggering for new files, or it might be failing before it can move them.

## Resolution

root_cause:
fix:
verification:
files_changed: []
