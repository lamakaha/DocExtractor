# 06-02 Summary: Durable Extraction Job Handoff

## Outcome
- Added a persisted `ExtractionJob` table in SQLite to serve as the handoff between ingestion and extraction.
- Implemented an `ExtractionJobService` with idempotent enqueue, explicit job claiming, retry-aware failure handling, and terminal job completion/failure states.
- Updated the watcher to stop after ingestion + enqueue instead of running extraction inline.
- Updated the CLI processor to drain queued extraction jobs rather than inferring pending work from `packages.status = INGESTED`.

## Why This Matters
- The pipeline now has a durable orchestration boundary instead of relying on inline watcher execution.
- Retry state and last-error metadata are explicit, which makes later observability and dead-letter work easier to layer in.
- This addresses one of the highest-priority architecture review findings without forcing a distributed queue rewrite.

## Validation
- `python -m pytest tests/test_extraction_job_service.py tests/test_watcher.py tests/test_extraction_pipeline.py -q --basetemp=C:\Users\sarka\OneDrive\Papa\DocExtractor\.pytest-lite-all`

## Remaining Work
- Multi-page and multi-attachment reconciliation still need an explicit package-level strategy.
- Job leasing is SQLite-local and not yet strong enough for multi-host workers.
- Observability is still thin around model metadata, token usage, and latency capture.
- Analytics/export shaping remains hardcoded and should move toward config-driven shredding.
