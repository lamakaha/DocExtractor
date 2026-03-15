def wait_for_app_ready(page):
    """
    Waits for Streamlit's loading indicator (stStatusWidget) to be hidden.
    This ensures that the Streamlit app has finished rendering and rerunning.
    """
    page.locator('[data-testid="stStatusWidget"]').wait_for(state="hidden", timeout=10000)
