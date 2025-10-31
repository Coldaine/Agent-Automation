
import atexit
import contextvars
from contextlib import contextmanager
import logging
import os
import sys
from pathlib import Path

from loguru import logger

# --- State Management -----------------------------------------------------------
_is_configured = False
_loguru_sink_ids: list[int] = []

# --- Context Variables for Correlation ------------------------------------------
request_id_var = contextvars.ContextVar("request_id", default=None)
correlation_id_var = contextvars.ContextVar("correlation_id", default=None)

# --- Interception for stdlib logging --------------------------------------------
class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Bind the stdlib logger's name to the 'extra' dict for correct context
        logger.bind(name=record.name).opt(depth=6, exception=record.exc_info).log(
            level, record.getMessage()
        )

# --- Main Configuration & Lifecycle ---------------------------------------------
def configure_logging(*, env: str | None = None, test_mode: bool = False,
                      log_dir: str | None = None, stdout_json: bool | None = None):
    """
    Idempotent. In tests set test_mode=True to avoid async/queue.
    """
    global _is_configured, _loguru_sink_ids
    if _is_configured:
        return
    _is_configured = True

    logger.remove()  # clear default sink

    env = (env or os.getenv("LOG_ENV", "prod")).lower()
    base_dir = Path(log_dir or os.getenv("LOG_DIR", "./logs"))
    base_dir.mkdir(parents=True, exist_ok=True)

    try:
        os.chmod(base_dir, 0o700)
    except Exception:
        pass

    serialize = (env == "prod")
    enqueue = False if test_mode else True

    # File Sinks
    app_path = base_dir / "app.log"
    errors_path = base_dir / "errors.log"

    _loguru_sink_ids.append(
        logger.add(app_path, level="INFO",
                   serialize=serialize, enqueue=enqueue, backtrace=False, diagnose=False)
    )
    _loguru_sink_ids.append(
        logger.add(errors_path, level="WARNING",
                   serialize=serialize, enqueue=enqueue, backtrace=False, diagnose=False)
    )

    # Console Sink
    mirror_json = (stdout_json if stdout_json is not None
                   else os.getenv("LOG_STDOUT_JSON", "false").lower() == "true")
    if env == "dev" and not mirror_json:
        _loguru_sink_ids.append(
            logger.add(sys.stdout, level="DEBUG", serialize=False,
                       enqueue=False, colorize=True, backtrace=False, diagnose=False)
        )
    elif mirror_json:
        _loguru_sink_ids.append(
            logger.add(sys.stdout, level="INFO", serialize=True,
                       enqueue=False, backtrace=False, diagnose=False)
        )

    # Stdlib Interception
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    atexit.register(shutdown_logging)

def shutdown_logging():
    """Flush and close all sinks deterministically."""
    global _is_configured
    if not _is_configured:
        return

    for sid in list(_loguru_sink_ids):
        try:
            logger.remove(sid)
        except Exception:
            pass
    _loguru_sink_ids.clear()
    _is_configured = False

@contextmanager
def with_correlation(request_id=None, correlation_id=None):
    token1 = request_id_var.set(request_id)
    token2 = correlation_id_var.set(correlation_id)
    try:
        yield
    finally:
        request_id_var.reset(token1)
        correlation_id_var.reset(token2)
