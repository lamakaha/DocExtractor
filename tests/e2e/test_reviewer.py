import pytest
from playwright.sync_api import Page, expect
from tests.e2e.utils import wait_for_app_ready

def test_reviewer_approval_flow(page: Page, seed_db_with_extraction):
    """
    Verifies that the reviewer view works properly:
    - Navigates to reviewer view
    - Interacts with form
    - Approves extraction
    - Returns to dashboard and verifies status updated
    """
    page.goto("http://localhost:8502")
    wait_for_app_ready(page)
    
    # Assert package is visible in dashboard
    expect(page.get_by_text("reviewer_test.zip").first).to_be_visible()
    
    # Click the "Review" button for the seeded package
    review_btn = page.get_by_role("button", name="Review").first
    expect(review_btn).to_be_visible()
    review_btn.click()
    
    # Wait for navigation to Reviewer view
    wait_for_app_ready(page)
    
    # Assert the page header contains "Review:"
    expect(page.get_by_text("Review: reviewer_test.zip").first).to_be_visible()
    
    # Find one of the text inputs for an extracted field, fill it with a new value
    textbox = page.get_by_role("textbox", name="lender_name").first
    expect(textbox).to_be_visible()
    expect(textbox).to_have_value("Original Bank")
    
    # Fill triggers typing
    textbox.fill("New Bank Value")
    
    # Press Enter or click outside to trigger the Streamlit rerun
    textbox.press("Enter")
    wait_for_app_ready(page)
    
    # Now wait again and verify the value is updated
    textbox = page.get_by_role("textbox", name="lender_name").first
    expect(textbox).to_have_value("New Bank Value")

    # Task 3: Approval Workflow Test
    # Click the "Approve" button
    approve_btn = page.get_by_role("button", name="Approve").first
    expect(approve_btn).to_be_visible()
    approve_btn.click()
    
    # Wait for routing back to Dashboard
    wait_for_app_ready(page)
    
    # Assert no stException occurred during the entire flow.
    expect(page.locator('[data-testid="stException"]').first).not_to_be_attached()
    
    # The app should route back to the Dashboard. Verify that the package status in the UI is now APPROVED.
    expect(page.get_by_text("Package Dashboard").first).to_be_visible()
    expect(page.get_by_text("APPROVED").first).to_be_visible()
