# ADR: Canonical PDF Pipeline Refresh

## Status
- Accepted

## Date
- 2026-03-15

## Context
- Current architecture:
  - Mixed source files are ingested and the extraction pipeline chooses a primary file dynamically.
  - PDFs are converted to images in the extraction stage.
  - Reviewer behavior assumes page + bbox evidence, but non-PDF/non-image flows are inconsistent.
- Current limitations:
  - The pipeline is too document-centric and too monolithic.
  - Bounding boxes are scaled to pixels before persistence even though the UI expects normalized coordinates.
  - The watcher runs ingestion and extraction inline with weak durability semantics.
  - Review evidence is not anchored to one consistent artifact across file types.
- Trigger for change:
  - Simplify the architecture while preserving a strong reviewer workflow.
  - Avoid an OCR-first text-only design.
- Constraints:
  - Keep the Streamlit reviewer page + bbox based.
  - Preserve the existing `.planning` workflow.
  - Minimize risky rewrites in the first implementation slice.

## Decision
- Chosen approach:
  - Normalize supported source files to a canonical PDF before extraction and review.
  - Use the canonical PDF as the review contract for the UI.
  - Persist normalized bbox coordinates as the durable source of truth.
  - Implement the architecture incrementally: canonicalization first, then job durability and reconciliation work.
- Scope:
  - Pipeline refresh for ingestion-to-extraction-to-review.
  - Planning changes for follow-on durability, reconciliation, and analytics improvements.
- Non-goals:
  - Full queue/worker redesign in the first slice.
  - Full spreadsheet support in the first slice.
  - Replacing SQLite or the current reviewer UI.

## Options Considered
### Option 1: OCR-first text pipeline
- Pros:
  - Simpler downstream text extraction on some documents.
  - Potentially cheaper for text-native files.
- Cons:
  - Weakens visual grounding.
  - Conflicts with the current reviewer contract.
  - Adds format-specific evidence handling in the UI.

### Option 2: Native mixed-format routing with format-specific review surfaces
- Pros:
  - Uses each source format directly.
  - Can optimize extraction path per input type.
- Cons:
  - Increases UI and provenance complexity.
  - Harder to keep one evidence model.

### Option 3: Canonical PDF review contract
- Pros:
  - Keeps one reviewer surface.
  - Preserves vision-first extraction.
  - Simplifies provenance to page + normalized bbox.
- Cons:
  - Conversion fidelity becomes critical infrastructure.
  - Some file types require additional canonicalization work.

## Consequences
- Benefits:
  - A consistent PDF-based reviewer contract.
  - Better alignment between extraction storage and UI expectations.
  - A cleaner migration path than a full rewrite.
- Risks:
  - Poor canonical PDF generation would degrade extraction quality.
  - Initial implementation will still inherit some monolithic/orchestration limits.
- Operational impact:
  - More CPU/memory for PDF normalization.
  - Later phases still need queueing and retries.
- Test impact:
  - Add canonicalization tests.
  - Add extraction pipeline tests for normalized bbox persistence and canonical PDF file linkage.

## Migration Plan
1. Introduce canonical PDF generation for currently supported non-spreadsheet types.
2. Update the extraction pipeline to extract from canonical PDFs and persist normalized boxes.
3. Keep the reviewer on PDF pages using the canonical file.
4. Add later phases for queued jobs, reconciliation, observability, and spreadsheet support.

## Rollback / Fallback
- Disable canonicalization for specific source types and fall back to the prior primary-file behavior if conversion quality is unacceptable.
- Preserve original source files so the prior pipeline path remains recoverable during migration.

## Traceability
- Requirements:
  - REQ-EXT-01, REQ-EXT-03, REQ-EXT-05, REQ-UI-02, REQ-UI-03, REQ-NFR-03
- Affected modules:
  - `src/services/extraction_pipeline.py`
  - `src/services/ingestor.py`
  - `src/ui/reviewer.py`
  - storage and planning artifacts
- Validation artifacts:
  - New phase 06 plan and implementation tests
