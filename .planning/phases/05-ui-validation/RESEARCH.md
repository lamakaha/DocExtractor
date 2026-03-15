# Phase 5: UI-Validation - Research

**Researched:** 2026-03-14
**Domain:** End-to-End Automated Testing for Streamlit using Playwright
**Confidence:** HIGH

*Note: Investigation was interrupted due to turn limits, but sufficient information was gathered to confidently plan this phase.*

## Summary

Automated UI testing for Streamlit applications is best handled using `pytest-playwright`. Because Streamlit reruns the entire Python script upon user interaction, tests must be designed to properly wait for these reruns to finish before making assertions. This is achieved by targeting specific Streamlit-injected DOM attributes like `data-testid="stStatusWidget"` or `data-testid="stException"`.

**Primary recommendation:** Use `pytest-playwright` with a `conftest.py` fixture that spawns the Streamlit app as a background subprocess, and write robust locator waits using Streamlit's native `data-testid` selectors.

## User Constraints

No `05-CONTEXT.md` was found, so there are no locked user decisions to restrict the implementation. The stack is defined by the `ROADMAP.md` and current application architecture.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REQ-UI-01 | Dashboard | Requires Playwright to interact with dashboard tables and buttons, ensuring state changes work without throwing Streamlit exceptions. |
| REQ-UI-02 | Side-by-side Review Interface | Requires tests to click "Review" on a package, navigate to the Reviewer view, and verify that the document viewer and extraction forms render without JS errors. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pytest` | 8.0+ | Test framework | Standard Python testing utility |
| `pytest-playwright` | 0.4+ | Browser automation | Easiest way to run Playwright in Python |
| `playwright` | 1.40+ | E2E Testing | Robust handling of dynamic single-page/Streamlit apps |

**Installation:**
```bash
pip install pytest pytest-playwright playwright
playwright install chromium
```

## Architecture Patterns

### Recommended Project Structure
```
tests/
├── conftest.py               # Contains the Streamlit subprocess fixture
├── e2e/                      # Playwright UI tests
│   ├── test_dashboard.py     # Tests for basic navigation & export
│   └── test_reviewer.py      # Tests for Reviewer UI interactions
```

### Pattern 1: Streamlit Subprocess Fixture
**What:** Spawning the Streamlit app before tests run.
**When to use:** Always, for E2E tests, to ensure the server is fresh and running.
**Example:**
```python
# tests/conftest.py
import pytest
import subprocess
import time

@pytest.fixture(scope="session", autouse=True)
def start_streamlit():
    process = subprocess.Popen(["streamlit", "run", "src/main.py", "--server.port=8501", "--server.headless=true"])
    time.sleep(3) # Wait for server to start
    yield
    process.terminate()
    process.wait()
```

### Pattern 2: Waiting for Streamlit Rerun
**What:** Waiting for the `stStatusWidget` (the "running" indicator) to disappear before proceeding.
**When to use:** After every interaction (click, input) that causes a Streamlit app rerun.
**Example:**
```python
def wait_for_app_ready(page):
    # The status widget appears when Streamlit is rerunning the script
    page.locator('[data-testid="stStatusWidget"]').wait_for(state="hidden", timeout=10000)
```

### Anti-Patterns to Avoid
- **Using `time.sleep()` in tests:** Hardcoding waits leads to flaky tests since Streamlit rerun times vary based on the workload. Always wait for specific `data-testid` states to be visible or hidden.
- **Relying on "networkidle":** Streamlit keeps a persistent WebSocket connection open, so `networkidle` state may never be reached or behave unpredictably.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Exception Detection | Custom JS log scraping | `page.get_by_test_id("stException")` | Streamlit standardizes how Python errors are displayed on the frontend via this specific `data-testid`. |
| Waiting for load | Custom timeouts | `page.get_by_test_id("stStatusWidget")` | Streamlit provides native DOM elements that appear during reruns. |

## Common Pitfalls

### Pitfall 1: Checking state before the rerun starts
**What goes wrong:** Tests interact with the UI, immediately check an assertion, and pass, but then the Streamlit app reruns and actually throws an error.
**Why it happens:** Playwright is faster than Streamlit's WebSocket round-trip to start the rerun.
**How to avoid:** Ensure tests explicitly wait for the loading state to finish (or wait for the new element to appear) before asserting.

### Pitfall 2: Port Conflicts
**What goes wrong:** `pytest` cannot start the Streamlit fixture because port `8501` is in use.
**Why it happens:** A previous test run didn't terminate the subprocess, or the user is running the dev server manually.
**How to avoid:** Always terminate the subprocess in the fixture teardown. Consider running E2E tests on a different port like `8502`.

## Code Examples

### Detecting Streamlit Exceptions
```python
from playwright.sync_api import Page, expect

def test_no_streamlit_exceptions(page: Page):
    page.goto("http://localhost:8501")
    wait_for_app_ready(page)
    
    # Check that no exception dialogs are on screen
    exception_box = page.locator('[data-testid="stException"]')
    expect(exception_box).not_to_be_attached()
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest-playwright |
| Config file | none detected |
| Quick run command | `pytest tests/e2e/ -v` |
| Full suite command | `pytest tests/e2e/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-UI-01 | Test Export feature from Dashboard | E2E | `pytest tests/e2e/test_dashboard.py` | ❌ Wave 0 |
| REQ-UI-02 | Test Reviewer UI Interaction | E2E | `pytest tests/e2e/test_reviewer.py` | ❌ Wave 0 |

### Wave 0 Gaps
- [ ] `tests/conftest.py` — Needs Streamlit startup fixture.
- [ ] `tests/e2e/` directory creation.
- [ ] `requirements.txt` — Needs `pytest-playwright` and `playwright`.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Playwright is the industry standard for E2E.
- Architecture: HIGH - Best practices for Streamlit specifically documented.
- Pitfalls: HIGH - Streamlit's execution model is well understood.