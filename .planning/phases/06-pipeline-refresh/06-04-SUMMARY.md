# 06-04 Summary: Config-Driven Analytical Shredding

## Outcome
- Extended document configs with `analytical_mappings` for summary and transaction shredding.
- Refactored `AnalyticalService` to build DuckDB summary and transaction views from config metadata instead of hardcoded JSON paths.
- Added analytical tests covering multiple document types and safe handling of document types without transaction mappings.

## Why This Matters
- New document types can now participate in analytics and export through configuration instead of Python code changes.
- The analytical layer no longer bakes one extraction shape into the service implementation.
- This closes the last major architecture gap called out in the original pipeline review for Phase 6.

## Validation
- `python -m pytest tests/test_analytical.py tests/test_export.py -q --basetemp=C:\Users\sarka\OneDrive\Papa\DocExtractor\.pytest-lite-06-04`

## Remaining Work
- Classification still uses first-page bias instead of richer package-level context.
- Config validation for malformed analytical mappings could be made stricter.
- Observability and model/runtime metadata remain lighter than the ideal target architecture.
