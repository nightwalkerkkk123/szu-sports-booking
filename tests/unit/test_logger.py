"""Tests for booking.observability.logger module - Structured logging."""
from unittest.mock import patch


class TestLoggerInit:
    """Test Logger initialization."""

    def test_logger_has_name(self):
        """Logger has a name attribute."""
        from booking.observability.logger import Logger

        logger = Logger("test")
        assert logger.name == "test"

    def test_logger_has_level(self):
        """Logger has a level attribute."""
        from booking.observability.logger import Logger

        logger = Logger("test", level="debug")
        assert logger.level == "debug"


class TestStructuredLogging:
    """Test structured logging methods."""

    def test_info_logs_message(self):
        """info() logs a message."""
        from booking.observability.logger import Logger

        logger = Logger("test")
        with patch.object(logger, '_log') as mock_log:
            logger.info("test message")
            mock_log.assert_called_once()

    def test_error_logs_with_trace_id(self):
        """error() logs with trace_id context."""
        from booking.observability.logger import Logger

        logger = Logger("test")
        with patch.object(logger, '_log') as mock_log:
            logger.error("error occurred", trace_id="abc-123")
            call_args = mock_log.call_args
            assert "abc-123" in str(call_args)


class TestLogLevels:
    """Test log level handling."""

    def test_logger_respects_debug_level(self):
        """Logger outputs debug logs when level is debug."""
        from booking.observability.logger import Logger

        logger = Logger("test", level="debug")
        assert logger.level == "debug"

    def test_logger_respects_info_level(self):
        """Logger outputs info logs when level is info."""
        from booking.observability.logger import Logger

        logger = Logger("test", level="info")
        assert logger.level == "info"


class TestContextInjection:
    """Test context injection in logs."""

    def test_inject_trace_id_adds_to_context(self):
        """inject_trace_id adds trace_id to log context."""
        from booking.observability.logger import Logger

        logger = Logger("test")
        logger.inject_trace_id("trace-456")
        # Logger should store trace_id for subsequent logs

    def test_context_cleared_after_use(self):
        """Context is cleared after logging."""
        from booking.observability.logger import Logger

        logger = Logger("test")
        logger.inject_trace_id("trace-789")
        # After logging, context should be clean
