# 06-01 Summary: Canonical PDF Foundation

## Outcome
- Added a canonical PDF normalization service for the current supported extraction inputs: PDF, images, plain text, HTML, and CSV.
- Updated the extraction pipeline to normalize the selected source document to a canonical PDF before classification and extraction.
- Persisted extraction records against the canonical PDF artifact instead of mixed source files.
- Stopped scaling bounding boxes to pixels before persistence; normalized `0-1000` coordinates now remain the stored source of truth.

## Why This Matters
- The reviewer contract is now cleaner for non-PDF sources because extraction points to a PDF artifact that can be rendered page-by-page.
- One of the prior review findings is directly addressed: stored bbox coordinates now match what the reviewer expects.
- The change is incremental; it does not force the queue/retry/durability rewrite into the same patch.

## Validation
- `python -m pytest tests/test_canonical_document_service.py tests/test_extraction_pipeline.py -q --basetemp=.pytest-tmp-canonical-2`

## Remaining Work
- Runtime durability: queued jobs, retries, idempotency.
- Multi-page reconciliation and package-level context improvements.
- Config-driven analytical shredding.
- Spreadsheet-specific canonicalization and reviewer verification.
