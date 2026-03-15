import pytest
from playwright.sync_api import Page, expect
from tests.e2e.utils import wait_for_app_ready

def test_dashboard_renders_packages(page: Page, seed_db):
    """
    Verifies that the dashboard correctly renders packages from the database.
    """
    page.goto("http://localhost:8502")
    wait_for_app_ready(page)

    # Check for package statuses
    expect(page.get_by_text("APPROVED").first).to_be_visible()
    expect(page.get_by_text("INGESTED").first).to_be_visible()

    # Check for filenames
    expect(page.get_by_text("ingested_doc.zip").first).to_be_visible()
    expect(page.get_by_text("approved_doc.zip").first).to_be_visible()

    # Assert no Streamlit exceptions
    expect(page.locator('[data-testid="stException"]').first).not_to_be_attached()

def test_dashboard_export_flow(page: Page, seed_db):
    """
    Verifies the bulk export flow on the dashboard.
    """
    page.goto("http://localhost:8502")
    wait_for_app_ready(page)

    # Click the "Prepare Bulk Export" button
    prepare_btn = page.get_by_role("button", name="Prepare Bulk Export")
    expect(prepare_btn).to_be_visible()
    prepare_btn.click()

    # Wait for processing
    wait_for_app_ready(page)

    # Verify the "⬇️ Download Approved Excel" button appears
    download_btn = page.get_by_role("button", name="⬇️ Download Approved Excel")
    expect(download_btn).to_be_visible()

    # Assert no Streamlit exceptions
    expect(page.locator('[data-testid="stException"]').first).not_to_be_attached()
