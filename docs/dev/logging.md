
# Durable, Structured Logging Guide

This guide details the file-first, structured logging system integrated into the DesktopOps Agent. It's designed for durability, performance, and great developer experience (DX).

## Quick Start

1.  **Run the agent**: No code changes are needed. The logging system is automatically configured on startup.
    ```bash
    make run
    ```
2.  **Tail the logs**: Open two terminals to tail the application and error logs.
    ```bash
    # Terminal 1: Application logs (INFO and above)
    tail -f logs/app.log | jq .

    # Terminal 2: Error logs (WARNING and above)
    tail -f logs/errors.log | jq .
    ```

## Configuration (Environment Variables)

The logging system is configured via environment variables. No code modifications are required for normal use.

| Variable                  | Default                                | Description                                                                                             |
| ------------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `LOG_ENV`                 | `prod`                                 | Set to `dev` for colorful, human-readable console logs. `prod` uses structured JSON.                    |
| `LOG_DIR`                 | `./logs`                               | Directory to store log files. Created automatically with secure permissions (`0700`).                   |
| `LOG_ROTATE_SIZE`         | `10485760` (10 MB)                     | Maximum size in bytes before a log file is rotated.                                                     |
| `LOG_RETENTION`           | `10 days`                              | How long to keep old log files (e.g., `"1 week"`, `"30 days"`).                                         |
| `LOG_SAMPLING_RATE`       | `1.0`                                  | A float between `0.0` and `1.0`. `0.5` logs 50% of records.                                             |
| `LOG_DEDUP_WINDOW_SEC`    | `0`                                    | Suppress duplicate log messages within this time window (in seconds). `0` disables it.                  |
| `LOG_STDOUT_JSON`         | `false`                                | In `prod` mode, mirror JSON logs to stdout. Useful for containerized environments.                      |
| `LOG_CAPTURE_PRINT`       | `false`                                | **Use with caution.** If `true`, redirects `print()` calls to the INFO log sink. Disabled by default.   |
| `SERVICE_NAME`            | `desktop-ops-agent`                    | Service name identifier in log records.                                                                 |
| `SERVICE_VERSION`         | `0.1.0`                                | Service version identifier in log records.                                                              |

## Log Schema (JSON)

All file logs and `prod` stdout logs are single-line JSON objects conforming to the following schema.

| Key                | Type   | Description                                                                 |
| ------------------ | ------ | --------------------------------------------------------------------------- |
| `ts`               | string | UTC timestamp in ISO 8601 format (e.g., `"2025-10-31T12:30:00.123Z"`).       |
| `level`            | string | Log level (`"INFO"`, `"WARNING"`, `"ERROR"`).                               |
| `logger`           | string | The name of the logger instance (e.g., `"agent.main"`).                     |
| `msg`              | string | The log message.                                                            |
| `module`           | string | The Python module where the log was emitted.                                |
| `func`             | string | The function name.                                                          |
| `line`             | number | The line number.                                                            |
| `pid`              | number | Process ID.                                                                 |
| `thread`           | number | Thread ID.                                                                  |
| `service`          | string | Name of the service (`desktop-ops-agent`).                                  |
| `version`          | string | Service version.                                                            |
| `env`              | string | Logging environment (`dev` or `prod`).                                      |
| `request_id`       | string | Unique ID for a specific request or task (via `with_correlation`).          |
| `correlation_id`   | string | ID to correlate logs across multiple services or tasks.                     |
| `trace_id`         | string | **(OTel)** OpenTelemetry Trace ID, if the OTel SDK is active.               |
| `span_id`          | string | **(OTel)** OpenTelemetry Span ID, if the OTel SDK is active.                |
| `extra`            | object | A dictionary for custom, structured data.                                   |
| `log_schema_version` | number | Schema version, starting at `1`.                                            |


## How It Works

- **Engine**: The system uses **Loguru** for its robust, non-blocking I/O (`enqueue=True`) and simple configuration.
- **Interception**: It automatically intercepts standard library `logging` calls, `warnings.warn()`, and optionally `print()` statements, so existing code works without modification.
- **Performance**: Logs are written to files from a separate process, ensuring that logging I/O does not block the main application thread.
- **Safety**: The log directory and files are created with restricted permissions (`0700` for the directory, `0600` for files) by default.

## OpenTelemetry (OTel) Note

The logger will automatically detect if an OpenTelemetry SDK is active in the environment. If it finds a valid trace context, it will automatically include `trace_id` and `span_id` in the log records, bridging the gap between logging and tracing.

## Change Log & Files Touched

### Files Created
- `observability/logging_config.py`: Core logging library.
- `tests/test_logging.py`: Unit tests for the new logging system.
- `tests/conftest.py`: Session-wide test configuration for logging.
- `docs/dev/logging.md`: This documentation file.

### Files Modified
- `agent/main.py`: Integrated `configure_logging()` at the application entry point.
- `requirements.txt`: Added `loguru>=0.7.2` to the project dependencies.

### Default Flags & Behavior
- **Logging Environment (`LOG_ENV`)**: Defaults to `prod`, enabling structured JSON logging to files.
- **Log Directory (`LOG_DIR`)**: Defaults to `./logs`.
- **Asynchronous Logging (`enqueue`)**: Enabled by default for performance in production, but disabled during tests for deterministic validation.
