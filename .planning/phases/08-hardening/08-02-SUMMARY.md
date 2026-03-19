# 08-02 Summary: Package-Level Selection and Reconciliation

## Outcome
- Replaced the old implicit primary-file heuristic with an explicit package-level candidate selection model in the extraction pipeline.
- Added support for primary, supporting-visual, supporting-text, and ignored artifact roles, and surfaced those decisions in structured pipeline logs and classification context.
- Tightened list reconciliation to deduplicate duplicate supporting evidence while preserving canonical-PDF page provenance for the chosen primary document.

## Why This Matters
- Mixed-file packages are now easier to reason about because the pipeline records why one artifact became the canonical extraction source and which other artifacts were treated as support.
- Classification receives a clearer package manifest instead of only a loosely assembled first-page context.
- Supporting artifacts can influence package interpretation without shifting field provenance away from the canonical PDF used for extraction and review.

## Validation
- `python -m pytest tests/test_classification.py tests/test_reconciliation_service.py tests/test_extraction_pipeline.py -q --basetemp=C:\Users\sarka\OneDrive\Papa\DocExtractor\.pytest-lite-08-02`

## Remaining Work
- The orchestrator is still relatively service-coupled; stage-boundary cleanup remains the next architectural hardening option if it is still worth the added complexity.
- Package selection is now explicit, but more advanced cross-artifact value synthesis is still intentionally bounded to keep provenance explainable.
