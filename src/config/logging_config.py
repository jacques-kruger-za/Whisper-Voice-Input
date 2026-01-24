"""Logging configuration with app-wide logger setup."""

import logging
import sys
from pathlib import Path
from typing import Optional
from platformdirs import user_log_dir

from .constants import APP_NAME, APP_AUTHOR

# Log format constants
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOG_LEVEL = logging.INFO


class LoggingConfig:
    """Manage application-wide logging configuration."""

    def __init__(self):
        self._log_dir = Path(user_log_dir(APP_NAME, APP_AUTHOR))
        self._log_file = self._log_dir / "app.log"
        self._configured = False
        self._root_logger: Optional[logging.Logger] = None

    def _ensure_log_dir(self) -> None:
        """Ensure log directory exists."""
        try:
            self._log_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError):
            pass  # Fall back to console-only logging

    def configure(self, level: int = DEFAULT_LOG_LEVEL) -> None:
        """Configure the root logger with file and console handlers."""
        if self._configured:
            return

        self._ensure_log_dir()

        # Create root logger for the app
        self._root_logger = logging.getLogger(APP_NAME)
        self._root_logger.setLevel(level)

        # Prevent propagation to root logger
        self._root_logger.propagate = False

        # Create formatter
        formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

        # Console handler (stderr)
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        self._root_logger.addHandler(console_handler)

        # File handler (if directory is writable)
        if self._log_dir.exists():
            try:
                file_handler = logging.FileHandler(
                    self._log_file, encoding="utf-8", mode="a"
                )
                file_handler.setLevel(level)
                file_handler.setFormatter(formatter)
                self._root_logger.addHandler(file_handler)
            except (OSError, PermissionError):
                pass  # Continue with console-only logging

        self._configured = True

    def get_logger(self, name: str) -> logging.Logger:
        """Get a named logger as a child of the app logger."""
        if not self._configured:
            self.configure()

        # Create child logger under app namespace
        return logging.getLogger(f"{APP_NAME}.{name}")

    @property
    def log_file(self) -> Path:
        """Get the log file path."""
        return self._log_file

    @property
    def log_dir(self) -> Path:
        """Get the log directory path."""
        return self._log_dir


# Global logging config instance
_logging_config: Optional[LoggingConfig] = None


def get_logging_config() -> LoggingConfig:
    """Get the global logging config instance."""
    global _logging_config
    if _logging_config is None:
        _logging_config = LoggingConfig()
    return _logging_config


def get_logger(name: str) -> logging.Logger:
    """Get a named logger for the application.

    Args:
        name: Logger name (will be prefixed with app name)

    Returns:
        Configured logger instance
    """
    return get_logging_config().get_logger(name)


def configure_logging(level: int = DEFAULT_LOG_LEVEL) -> None:
    """Configure app-wide logging.

    Args:
        level: Log level (default: INFO)
    """
    get_logging_config().configure(level)
