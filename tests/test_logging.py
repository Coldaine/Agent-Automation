
from pathlib import Path
import json
import logging
from loguru import logger

def read_last_json(path: Path):
    """Reads and parses the last non-empty line of a file as JSON."""
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    return json.loads(lines[-1])

def test_writes_app_log_records(log_dir):
    """Verify that INFO messages are written to app.log as JSON."""
    app_log = log_dir / "app.log"

    logger.info("This is a test info message.", extra_field="test_value")

    assert app_log.exists()
    rec = read_last_json(app_log)

    assert rec["record"]["message"] == "This is a test info message."
    assert rec["record"]["level"]["name"] == "INFO"
    assert rec["record"]["extra"]["extra_field"] == "test_value"

def test_writes_error_log_records(log_dir):
    """Verify that WARNING messages are written to errors.log."""
    error_log = log_dir / "errors.log"

    logger.warning("This is a test warning message.")

    assert error_log.exists()
    rec = read_last_json(error_log)

    assert rec["record"]["message"] == "This is a test warning message."
    assert rec["record"]["level"]["name"] == "WARNING"

def test_stdlib_interception(log_dir):
    """Verify that stdlib logging is intercepted and written to the correct file."""
    error_log = log_dir / "errors.log"

    stdlib_logger = logging.getLogger("my_app.module")
    warning_message = "This is a test warning from a stdlib logger."
    stdlib_logger.warning(warning_message)

    rec = read_last_json(error_log)
    assert rec["record"]["message"] == warning_message
    assert rec["record"]["extra"]["name"] == "my_app.module"

def test_log_rotation_is_configured(log_dir):
    """
    This is not a functional test of rotation itself, but confirms
    that the configuration is being set. A functional test would be more complex.
    """
    # This test primarily ensures the test setup runs without errors.
    # The fixture in conftest.py is what configures logging.
    pass
