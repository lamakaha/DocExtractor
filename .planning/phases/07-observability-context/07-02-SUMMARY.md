# 07-02 Summary: Observability Reporting and Failure Diagnostics

## Outcome
- Added dashboard-friendly parsing and formatting for structured `PackageLog.details` metadata.
- Exposed latest extraction job retry/failure state through UI query helpers.
- Updated queue logging to emit structured attempt/status/error details for enqueue, claim, completion, and failure transitions.
- Extended the dashboard log view to show metadata and diagnostics columns instead of only free-text messages.

## Why This Matters
- Operators can now inspect model, prompt, latency, and retry/failure context from the dashboard without manually decoding JSON or querying SQLite.
- Failure diagnostics are easier to understand because queue state and last error are surfaced next to the relevant logs.
- This builds directly on `07-01` by making the captured observability data usable.

## Validation
- `python -m pytest tests/test_ui_queries.py tests/test_dashboard.py -q --basetemp=C:\Users\sarka\OneDrive\Papa\DocExtractor\.pytest-lite-07-02`

## Remaining Work
- Observability data is visible in the dashboard, but there is still no aggregate reporting view over failures and latency trends.
- Package-context selection could still be improved beyond the current bounded heuristic.
- Sensitive log-detail filtering remains policy-based rather than centrally enforced.
