"""Logging utilities for NexusEnrichmentAgent."""

import logging
import sys
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Session timestamp for tracing
_session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")


def get_session_timestamp() -> str:
    """Get the current session timestamp for tracing."""
    return _session_timestamp


class StreamingCallbackHandler:
    """
    Callback handler for streaming agent responses.

    This handler can be used with strands Agent to capture streaming output.
    """

    def __init__(self, stream: bool = False, output_stream=None):
        """
        Initialize the callback handler.

        Args:
            stream: Whether to stream output to console.
            output_stream: Optional stream to write output to (default: sys.stdout).
        """
        self.stream = stream
        self.output_stream = output_stream or sys.stdout
        self.buffer = []

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Handle new token from LLM."""
        self.buffer.append(token)
        if self.stream:
            self.output_stream.write(token)
            self.output_stream.flush()

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Handle LLM completion."""
        if self.stream:
            self.output_stream.write("\n")
            self.output_stream.flush()

    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """Handle LLM error."""
        logger.error(f"LLM error: {error}")

    def get_output(self) -> str:
        """Get the accumulated output."""
        return "".join(self.buffer)

    def clear(self) -> None:
        """Clear the buffer."""
        self.buffer = []


def get_callback_handler(stream: bool = False) -> StreamingCallbackHandler:
    """
    Get a callback handler instance.

    Args:
        stream: Whether to stream output to console.

    Returns:
        StreamingCallbackHandler instance.
    """
    return StreamingCallbackHandler(stream=stream)


def setup_logging(level: int = logging.INFO, format_string: Optional[str] = None) -> None:
    """
    Setup logging configuration.

    Args:
        level: Logging level (default: INFO).
        format_string: Custom format string (optional).
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(level=level, format=format_string, handlers=[logging.StreamHandler()])
