"""Unit tests for logging module."""

import logging

from continuous_wave.logging import ColoredFormatter, get_logger, setup_logging


class TestLogging:
    """Tests for logging configuration."""

    def test_setup_logging_default(self) -> None:
        """Test logging setup with default parameters."""
        setup_logging()
        logger = logging.getLogger("continuous_wave")
        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0

    def test_setup_logging_debug_level(self) -> None:
        """Test logging setup with DEBUG level."""
        setup_logging(level=logging.DEBUG)
        logger = logging.getLogger("continuous_wave")
        assert logger.level == logging.DEBUG

    def test_setup_logging_custom_format(self) -> None:
        """Test logging setup with custom format string."""
        custom_format = "%(levelname)s - %(message)s"
        setup_logging(format_string=custom_format)
        logger = logging.getLogger("continuous_wave")
        assert len(logger.handlers) > 0

    def test_setup_logging_no_color(self) -> None:
        """Test logging setup without color."""
        setup_logging(use_color=False)
        logger = logging.getLogger("continuous_wave")
        assert len(logger.handlers) > 0
        # Verify formatter is not ColoredFormatter
        handler = logger.handlers[0]
        assert not isinstance(handler.formatter, ColoredFormatter)

    def test_get_logger(self) -> None:
        """Test get_logger function."""
        logger = get_logger(__name__)
        assert isinstance(logger, logging.Logger)
        assert logger.name.startswith("continuous_wave")

    def test_get_logger_with_module_name(self) -> None:
        """Test get_logger with module name."""
        logger = get_logger("test_module")
        assert logger.name == "continuous_wave.test_module"

    def test_colored_formatter(self) -> None:
        """Test ColoredFormatter."""
        formatter = ColoredFormatter("%(levelname)s - %(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        assert "Test message" in formatted
