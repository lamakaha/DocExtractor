from playwright.sync_api import Page, expect
from tests.e2e.utils import wait_for_app_ready

def test_no_streamlit_exceptions(page: Page, seed_db):
    """
    Navigates to the Streamlit app and verifies there are no Python exceptions displayed.
    """
    page.goto("http://localhost:8502")
    wait_for_app_ready(page)
    
    # Check that no exception dialogs are on screen
    exception_box = page.locator('[data-testid="stException"]')
    expect(exception_box).not_to_be_attached()
