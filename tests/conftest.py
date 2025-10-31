
import os
import pytest
from pathlib import Path

@pytest.fixture(scope="function")
def log_dir(tmp_path):
    """
    Provides a function-scoped temporary directory for log files,
    ensuring each test has a clean logging environment.
    """
    # tmp_path is a built-in function-scoped fixture from pytest
    return tmp_path / "logs"

@pytest.fixture(scope="function", autouse=True)
def configure_test_logging(log_dir, monkeypatch):
    """
    This fixture is now function-scoped to resolve the ScopeMismatch error
    with the 'monkeypatch' fixture. It configures logging before each test
    and shuts it down afterward, ensuring complete test isolation.
    """
    # Ensure a clean environment for deterministic behavior for each test
    monkeypatch.setenv("LOG_ENV", "prod")
    monkeypatch.setenv("LOG_DIR", str(log_dir))
    monkeypatch.delenv("LOG_STDOUT_JSON", raising=False)

    from observability.logging_config import configure_logging, shutdown_logging

    # Configure logging for the test. test_mode=True makes it synchronous.
    configure_logging(test_mode=True)

    yield  # The test runs here.

    # Teardown: shutdown logging completely after the test.
    # The shutdown function handles resetting the internal state.
    shutdown_logging()
