"""
AWS CloudWatch structured logging configuration.

Provides JSON-formatted logs that integrate seamlessly with:
- CloudWatch Logs
- CloudWatch Logs Insights
- AWS CloudTrail
- X-Ray tracing
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional


class CloudWatchFormatter(logging.Formatter):
    """Format logs as JSON for CloudWatch Logs Insights."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "function": record.funcName,
            "line": record.lineno,
            "module": record.module,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        if hasattr(record, 'request_id'):
            log_data["request_id"] = record.request_id

        if hasattr(record, 'control_id'):
            log_data["control_id"] = record.control_id

        if hasattr(record, 'execution_time_ms'):
            log_data["execution_time_ms"] = record.execution_time_ms

        # Add any custom fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'msecs',
                          'message', 'pathname', 'process', 'processName', 'relativeCreated',
                          'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info']:
                if not key.startswith('_'):
                    log_data[key] = value

        return json.dumps(log_data)


def configure_cloudwatch_logging(
    service_name: str,
    log_level: str = "INFO",
    enable_console: bool = True
) -> logging.Logger:
    """
    Configure CloudWatch-compatible logging.

    Args:
        service_name: Name of the service (e.g., 'nexus-ecs-service')
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        enable_console: Whether to log to console (stdout)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(CloudWatchFormatter())
        logger.addHandler(console_handler)

    logger.propagate = False

    return logger


class StructuredLogger:
    """
    Wrapper for structured logging with CloudWatch.

    Usage:
        logger = StructuredLogger("nexus-ecs-service")
        logger.info("Processing request", control_id="IAM.21", execution_time_ms=150)
    """

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def _log(self, level: str, message: str, **kwargs):
        """Log with structured fields."""
        extra = {k: v for k, v in kwargs.items()}
        getattr(self.logger, level)(message, extra=extra)

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log('debug', message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log('info', message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log('warning', message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message."""
        self._log('error', message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self._log('critical', message, **kwargs)
