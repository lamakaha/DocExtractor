# 08-01 Summary: Runtime Hardening

## Outcome
- Added explicit stale-claim recovery to the durable extraction job flow so abandoned `PROCESSING` jobs are no longer reclaimed implicitly.
- Introduced a terminal `DEAD_LETTER` queue state for jobs that exhaust their retry budget or are recovered after a stale claim with no retries remaining.
- Expanded queue-service tests to cover stale-claim recovery, retry exhaustion, and the rule that terminal jobs are not silently revived by a later enqueue.

## Why This Matters
- Queue recovery is now easier to reason about because stale claims transition through a deliberate recovery path instead of being mixed into ordinary claiming logic.
- Retry exhaustion is now operationally explicit, which reduces ambiguity between “failed but still retryable” and “requires operator attention.”
- The watcher and worker flow keep the existing persisted-job model, but with stronger protection against stuck or repeatedly recycled jobs.

## Validation
- `python -m pytest tests/test_extraction_job_service.py tests/test_watcher.py tests/test_extraction_pipeline.py -q --basetemp=C:\Users\sarka\OneDrive\Papa\DocExtractor\.pytest-lite-08-01`

## Remaining Work
- Package-level selection and reconciliation is still heuristic and remains the next major architecture gap.
- The orchestrator is still service-coupled; stage-boundary cleanup has not been revisited yet.
- Queue recovery is stronger now, but there is still room for more operator controls such as explicit replay or manual dead-letter requeue tooling if scale requires it.
