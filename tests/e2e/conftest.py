import os
import sys
import time
import subprocess
import pytest

@pytest.fixture(scope="session", autouse=True)
def start_streamlit():
    """
    Spawns the Streamlit app before E2E tests run.
    Ensures test data isolation and dummy API keys are used.
    """
    env = os.environ.copy()
    env["DATABASE_URL"] = "sqlite:///test_e2e.db"
    env["OPENROUTER_API_KEY"] = "dummy"

    # Start the Streamlit application
    # using sys.executable -m streamlit to ensure we use the correct python environment
    process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "src/ui/app.py", "--server.port=8502", "--server.headless=true"],
        env=env
    )
    
    # Wait for the server to spin up
    time.sleep(5)
    
    yield
    
    # Terminate the server after tests complete
    process.terminate()
    process.wait()
