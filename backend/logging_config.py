"""
Structured JSON logging configuration for Safe YouTube Viewer.

Provides centralized logging setup with JSON formatting for production
observability and log aggregation.

Story 5.4 AC 3-5: Application logging with JSON structured format.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """
    Custom formatter for structured JSON logs.

    Outputs log records as JSON objects with timestamp, level, message,
    and contextual fields for structured logging systems.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON string.

        Args:
            record: LogRecord instance containing log event information

        Returns:
            JSON-formatted string with log entry fields
        """
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_entry.update(record.extra)

        return json.dumps(log_entry)


def setup_logging(log_file_path: str | None = None, log_level: str = "INFO") -> None:
    """
    Initialize application logging with JSON format.

    Configures root logger with file handler for structured JSON logging.
    Creates log directory if it doesn't exist.

    Args:
        log_file_path: Path to log file. Defaults to /var/log/youtube-viewer/app.log
                       in production, or /tmp/claude/app.log for testing.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                   Defaults to INFO.

    Story 5.4 AC 3-5: Configure JSON logging to /var/log/youtube-viewer/app.log
    """
    # Default log file path
    if log_file_path is None:
        # Try environment variable first, then default to production path
        log_file_path = os.getenv("LOG_FILE", "/var/log/youtube-viewer/app.log")

    log_path = Path(log_file_path)

    # Create log directory if it doesn't exist
    # If permission denied (dev/test environment), fall back to /tmp/claude/
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        # Fall back to temp directory for development/testing
        log_path = Path("/tmp/claude/app.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_file_path = str(log_path)

    # Create file handler with JSON formatter
    handler = logging.FileHandler(log_path)
    handler.setFormatter(JSONFormatter())

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Add JSON file handler
    root_logger.addHandler(handler)

    # Log initialization
    root_logger.info(f"JSON logging initialized: {log_file_path} (level: {log_level})")
