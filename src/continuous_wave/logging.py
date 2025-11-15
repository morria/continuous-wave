"""Structured logging configuration for continuous-wave.

This module provides centralized logging configuration with consistent formatting
and levels across the entire library. It's designed to help Claude Code easily
see what's happening during testing and development.
"""

import logging
import sys


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color output for better readability."""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[0;36m",  # Cyan
        "INFO": "\033[0;32m",  # Green
        "WARNING": "\033[0;33m",  # Yellow
        "ERROR": "\033[0;31m",  # Red
        "CRITICAL": "\033[0;35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with colors."""
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS and sys.stderr.isatty():
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"

        # Format the message
        result = super().format(record)

        # Reset level name for future use
        record.levelname = levelname

        return result


def setup_logging(
    level: int = logging.INFO,
    format_string: str | None = None,
    use_color: bool = True,
) -> None:
    """Configure logging for the continuous-wave library.

    This function sets up structured logging with consistent formatting across
    the library. It's automatically called when the library is imported, but
    can be reconfigured by calling this function again.

    Args:
        level: Logging level (default: INFO)
        format_string: Custom format string (default: structured format)
        use_color: Whether to use colored output (default: True)

    Example:
        >>> from continuous_wave.logging import setup_logging
        >>> import logging
        >>> setup_logging(level=logging.DEBUG)
    """
    # Default format string with all useful information
    if format_string is None:
        format_string = (
            "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(funcName)s | %(message)s"
        )

    # Create formatter
    formatter: logging.Formatter
    if use_color:
        formatter = ColoredFormatter(
            format_string,
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        formatter = logging.Formatter(
            format_string,
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Configure root logger
    root_logger = logging.getLogger("continuous_wave")
    root_logger.setLevel(level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Add console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Prevent propagation to root logger
    root_logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        Configured logger instance

    Example:
        >>> from continuous_wave.logging import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing audio chunk")
    """
    # Ensure name is prefixed with package name
    if not name.startswith("continuous_wave"):
        name = f"continuous_wave.{name}"

    return logging.getLogger(name)


# Configure logging with sensible defaults when module is imported
# This can be overridden by calling setup_logging() explicitly
setup_logging()
