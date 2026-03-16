# Phase 5: UI-Validation - Validation Plan

**Phase:** 05-ui-validation
**Goal:** Automated End-to-End Testing of the Streamlit UI to catch JS errors and regressions.

## Success Criteria Validation

| Criterion | Validation Approach |
|-----------|---------------------|
| 1. Playwright tests navigate to `http://localhost:8501`. | Verify that running the test suite automatically boots the Streamlit server and successfully connects to the index page. |
| 2. Tests interact with the "Reviewer" and "Export" features automatically. | Verify that tests simulate user clicks on the "Review" button, interact with the UI form, and click the "Export" button on the Dashboard. |
| 3. Validates no JavaScript errors or Streamlit exception dialogs appear. | Verify that the tests explicitly assert `page.locator('[data-testid="stException"]').is_hidden()` throughout the user journeys. |

## End-to-End Workflow Validation

1. **Dashboard Flow:** Run the suite. Tests should assert that packages are visible in the data table and the Export button functions properly.
2. **Reviewer Flow:** Run the suite. Tests should navigate to the Reviewer, verify that the PDF/Image renders correctly, input new values into the extraction form, and click Approve.
3. **Resilience:** Purposefully break a component in Streamlit (e.g., throwing a `ValueError` on button click) and verify that the Playwright tests catch the `stException` dialog and fail the suite.

## Verification Command
```bash
pytest tests/e2e/ -v
```