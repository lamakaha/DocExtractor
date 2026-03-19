# Paydown Manual Fixtures

Synthetic documents for manual testing of the paydown pipeline.

Files:
- `case-01-paydown-notice.txt`
  - single-file paydown notice
- `case-02-cover-email.eml`
  - supporting email body for a mixed package
- `case-02-paydown-notice.txt`
  - intended primary paydown notice
- `case-02-backup-statement.txt`
  - secondary supporting document that should not outrank the main notice
- `case-02-transactions.csv`
  - supporting transaction worksheet
- `case-03-near-miss.txt`
  - looks related but should be harder to classify as a paydown

Suggested manual use:
- Copy `case-01-paydown-notice.txt` into `ingest/` for a basic single-document run.
- Bundle the `case-02-*` files into one package for mixed-package selection testing.
- Use `case-03-near-miss.txt` as a negative or ambiguity check.
