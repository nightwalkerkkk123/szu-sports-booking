"""Structured logging for booking system."""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


# Global logger instances registry
_loggers: dict[str, "Logger"] = {}


class Logger:
    """Structured logger with JSON output and trace context."""

    def __init__(
        self,
        name: str = "booking",
        level: str = "info",
        log_dir: str = "logs",
        rotation: str = "daily",
        retention_days: int = 7,
    ):
        """Initialize logger.

        Args:
            name: Logger name (usually module name)
            level: Log level (debug, info, warning, error)
            log_dir: Directory for log files
            rotation: Log rotation strategy (daily, hourly)
            retention_days: Days to retain logs
        """
        self.name = name
        self.level = level
        self.log_dir = Path(log_dir) / name
        self.rotation = rotation
        self.retention_days = retention_days
        self._context: dict[str, Any] = {}

        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Set up Python logger
        self._logger = logging.getLogger(name)
        self._logger.setLevel(getattr(logging, level.upper()))
        if not self._logger.handlers:
            self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Set up console and file handlers."""
        from logging.handlers import TimedRotatingFileHandler

        # Console handler - human readable
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, self.level.upper()))
        console_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        self._logger.addHandler(console_handler)

        # JSON file handler - for machine reading
        json_handler = TimedRotatingFileHandler(
            self.log_dir / f"{self.name}.json.log",
            when="midnight" if self.rotation == "daily" else "H",
            interval=1,
            backupCount=self.retention_days,
        )
        json_handler.setLevel(getattr(logging, self.level.upper()))
        json_handler.setFormatter(JsonFormatter())
        self._logger.addHandler(json_handler)

        # Human-readable file handler - for direct reading
        text_handler = TimedRotatingFileHandler(
            self.log_dir / f"{self.name}.human.log",
            when="midnight" if self.rotation == "daily" else "H",
            interval=1,
            backupCount=self.retention_days,
        )
        text_handler.setLevel(getattr(logging, self.level.upper()))
        text_handler.setFormatter(HumanReadableFormatter())
        self._logger.addHandler(text_handler)

    def inject_trace_id(self, trace_id: str) -> None:
        """Inject trace_id into log context."""
        self._context["trace_id"] = trace_id

    def clear_context(self) -> None:
        """Clear log context."""
        self._context = {}

    def _log(
        self,
        level: int,
        message: str,
        **kwargs: Any,
    ) -> None:
        """Internal log method with context injection."""
        extra_data = {**self._context, **kwargs}
        record = logging.LogRecord(
            self.name,
            level,
            "",
            0,
            message,
            (),
            None,
        )
        record.extra = extra_data
        self._logger.handle(record)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self._log(logging.ERROR, message, **kwargs)


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "extra"):
            data.update(record.extra)

        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)

        return json.dumps(data, ensure_ascii=False)


class HumanReadableFormatter(logging.Formatter):
    """Human-readable formatter that shows extra fields inline."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record in human-readable form."""
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        level = record.levelname
        message = record.getMessage()

        result = f"{timestamp} | {level} | {message}"

        if hasattr(record, "extra") and record.extra:
            extra_parts = []
            for k, v in record.extra.items():
                if k != "trace_id":  # Skip trace_id for readability
                    extra_parts.append(f"{k}={v}")
            if extra_parts:
                result += " | " + " | ".join(extra_parts)

        return result


def get_logger(name: str = "booking") -> Logger:
    """Get or create a logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return Logger(name)