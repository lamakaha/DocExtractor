# 06-03 Summary: Multi-Page Reconciliation

## Outcome
- Added a reconciliation service that merges ordered page-level extraction results into one package-level extraction payload.
- Updated the extraction pipeline to persist a single reconciled extraction record per package while preserving `page_number` and bbox evidence for each field.
- Updated the reviewer so locating a reconciled field jumps to the correct canonical PDF page instead of assuming one extraction row per page.

## Why This Matters
- The pipeline no longer leaves multi-page packages fragmented into page-level extraction rows.
- The reviewer contract remains page + bbox based, but the extracted data contract is now package-level and coherent.
- This directly addresses one of the main architecture review gaps without forcing a larger schema or UI redesign.

## Validation
- `python -m pytest tests/test_reconciliation_service.py tests/test_extraction_pipeline.py tests/test_ui_form.py -q --basetemp=C:\Users\sarka\OneDrive\Papa\DocExtractor\.pytest-lite-06-03`

## Remaining Work
- Classification still anchors on the first page rather than full package context.
- Reconciliation rules are intentionally simple and may need document-type-specific merge policy later.
- Config-driven analytics/export shaping is still pending as the next major Phase 6 slice.
