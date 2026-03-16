# ADR: Durable Extraction Job Handoff

## Status
- Accepted

## Date
- 2026-03-15

## Context
- Current architecture:
  - Ingestion persists package files to SQLite and the watcher immediately calls the extraction pipeline inline.
  - The CLI batch processor scans `packages.status = INGESTED` directly instead of consuming a durable job queue.
  - Package logs and package statuses exist, but there is no persisted extraction work item with attempts, lease metadata, or retry state.
- Current limitations:
  - Watcher crashes or process restarts can interrupt extraction with no durable claim record.
  - The same package can be picked up by different entrypoints without a stable queue boundary.
  - Retry semantics and failure metadata are implicit in logs instead of explicit in orchestration state.
- Trigger for change:
  - Address the prior architecture review finding that the runtime pipeline is not durable enough.
  - Preserve the canonical-PDF architecture while introducing a safer handoff between ingestion and extraction.
- Constraints:
  - Keep SQLite as the transactional store for this phase.
  - Avoid a distributed queue rewrite in the first durability slice.
  - Preserve compatibility with the current Streamlit dashboard and package status model.

## Decision
- Chosen approach:
  - Add a persisted `ExtractionJob` record in SQLite as the extraction handoff for each package.
  - Make enqueue idempotent per package/job type instead of letting multiple entrypoints infer work from package status alone.
  - Have workers claim jobs by updating job status/attempt metadata before running extraction.
  - Requeue failed jobs until `max_attempts` is reached, then mark the job terminally failed.
- Scope:
  - SQLite-backed extraction jobs for claim/retry/failure tracking.
  - Watcher and CLI orchestration updates to consume jobs instead of inline extraction.
- Non-goals:
  - Distributed worker coordination across multiple hosts.
  - Full dead-letter storage outside SQLite.
  - Replacing package status transitions or the canonical PDF extraction path.

## Options Considered
### Option 1: Keep package-status scanning only
- Pros:
  - Minimal code change.
  - No schema updates.
- Cons:
  - No durable retry metadata or claim boundary.
  - Entry points remain tightly coupled to package status heuristics.

### Option 2: Add SQLite-backed extraction jobs
- Pros:
  - Smallest durable handoff that fits the current architecture.
  - Explicit attempt and failure tracking.
  - Enables retry/idempotency improvements without a queue rewrite.
- Cons:
  - Adds another transactional table and orchestration service.
  - SQLite still limits multi-process scalability.

### Option 3: Adopt an external queue now
- Pros:
  - Better long-term worker scaling and lease semantics.
- Cons:
  - Too large and risky for the next safe brownfield slice.
  - Would force broader operational changes immediately.

## Consequences
- Benefits:
  - Ingestion and extraction now have a persisted boundary.
  - Retry state becomes queryable and testable.
  - The watcher no longer performs extraction inline.
- Risks:
  - SQLite job claiming is still single-node oriented.
  - Existing status-driven assumptions may linger in old code paths if not updated carefully.
- Operational impact:
  - More SQLite writes for enqueue/claim/retry events.
  - Operators need to run the worker path to drain queued jobs.
- Test impact:
  - Add unit coverage for enqueue/claim/retry behavior.
  - Update watcher tests to validate enqueue handoff instead of inline extraction.

## Migration Plan
1. Add the `ExtractionJob` schema and a small orchestration service.
2. Update the watcher to ingest and enqueue instead of extracting inline.
3. Update the CLI processor to claim and execute jobs.
4. Add targeted tests for queue semantics and watcher handoff.

## Rollback / Fallback
- Revert the watcher and CLI to the prior direct `process_package` calls if job orchestration proves unstable.
- Existing package and extraction tables remain intact, so extraction logic can still run directly during rollback.

## Traceability
- Requirements:
  - REQ-NFR-03
  - REQ-EXT-01
- Affected modules:
  - `src/models/schema.py`
  - `src/services/watcher.py`
  - `src/services/extraction_pipeline.py`
  - `src/main.py`
- Validation artifacts:
  - `06-02-PLAN.md`
  - targeted pytest coverage for jobs, watcher, and pipeline worker flow
