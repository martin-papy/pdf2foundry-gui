"""
Centralized error handling and logging infrastructure for PDF2Foundry GUI.

This module provides a singleton ErrorHandler that captures, logs, and translates
exceptions into user-friendly messages while maintaining full diagnostic information.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
import threading
import traceback
from pathlib import Path
from typing import Any, ClassVar

from PySide6.QtCore import QObject, QStandardPaths, Signal

from .config import APP_NAME, APP_ORGANIZATION
from .errors import BaseAppError, from_exception


class ErrorHandler(QObject):
    """
    Centralized error handler with logging and user message translation.

    This singleton class provides comprehensive error handling including:
    - Exception capture and normalization
    - Structured logging with rotation
    - User-friendly message generation
    - Qt signal emission for UI integration
    """

    # Signal emitted when an error occurs (thread-safe)
    errorOccurred = Signal(object)  # BaseAppError

    _instance: ClassVar[ErrorHandler | None] = None
    _logger: ClassVar[logging.Logger | None] = None

    def __new__(cls) -> ErrorHandler:
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the error handler (called only once due to singleton)."""
        if hasattr(self, "_initialized"):
            return

        super().__init__()
        self._initialized = True
        self._original_excepthook = sys.excepthook
        self._original_threading_excepthook = getattr(threading, "excepthook", None)

        # Initialize logging
        self._setup_logging()

    def capture(self, exception: Exception, context: dict[str, Any] | None = None) -> BaseAppError:
        """
        Capture and normalize an exception into a BaseAppError.

        Args:
            exception: The exception to capture
            context: Optional context information

        Returns:
            BaseAppError with normalized metadata
        """
        # Sanitize context to prevent sensitive data leakage
        safe_context = self._sanitize_context(context or {})

        # Convert to BaseAppError using the error hierarchy
        app_error = from_exception(exception, safe_context)

        # Add additional metadata
        if not app_error.technical_message:
            app_error.technical_message = f"{type(exception).__name__}: {exception}"

        # Add traceback to context if not already present
        if "traceback" not in app_error.context:
            # Try to get current traceback, fallback to exception info
            tb_str = traceback.format_exc()
            if tb_str == "NoneType: None\n":
                # Not in exception context, create traceback from exception
                tb_str = f"{type(exception).__name__}: {exception}\n"
            app_error.context["traceback"] = tb_str

        return app_error

    def handle(self, exception: Exception, context: dict[str, Any] | None = None) -> BaseAppError:
        """
        Handle an exception by capturing, logging, and emitting signals.

        Args:
            exception: The exception to handle
            context: Optional context information

        Returns:
            BaseAppError for further processing
        """
        # Don't handle system exit or keyboard interrupt
        if isinstance(exception, SystemExit | KeyboardInterrupt):
            raise exception

        # Capture and normalize the exception
        app_error = self.capture(exception, context)

        # Log the error with full details
        if self._logger:
            self._logger.error(
                f"[{app_error.code.value}] {app_error.user_message}",
                extra={
                    "app_code": app_error.code.value,
                    "error_type": app_error.type.value,
                    "severity": app_error.severity.value,
                    "retriable": app_error.retriable,
                },
                exc_info=exception,
            )

        # Emit signal for UI components (thread-safe)
        self.errorOccurred.emit(app_error)

        return app_error

    def to_user_message(self, app_error: BaseAppError) -> str:
        """
        Generate a concise, user-friendly message from a BaseAppError.

        Args:
            app_error: The error to convert

        Returns:
            User-friendly message string
        """
        # Use the user_message from the error, which should already be friendly
        message = app_error.user_message

        # Add a hint for retriable errors
        if app_error.retriable:
            message += " You can try again."

        return message

    def _setup_logging(self) -> None:
        """Set up rotating file logging in the app data directory."""
        try:
            # Get app data directory
            app_data_location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)

            if not app_data_location:
                # Fallback to config location
                app_data_location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.ConfigLocation)
                app_data_path = Path(app_data_location) / APP_ORGANIZATION / APP_NAME
            else:
                app_data_path = Path(app_data_location)

            # Create logs directory
            logs_dir = app_data_path / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)

            # Set up logger
            ErrorHandler._logger = logging.getLogger("pdf2foundry_gui.errors")
            if ErrorHandler._logger:
                ErrorHandler._logger.setLevel(logging.DEBUG)
                ErrorHandler._logger.propagate = False

            # Avoid duplicate handlers
            if ErrorHandler._logger and not ErrorHandler._logger.handlers:
                # File handler with rotation
                log_file = logs_dir / "app.log"
                file_handler = logging.handlers.RotatingFileHandler(
                    log_file,
                    maxBytes=5_242_880,  # 5MB
                    backupCount=5,
                    encoding="utf-8",
                )

                # Formatter with error code
                formatter = logging.Formatter(
                    "%(asctime)s | %(levelname)s | %(name)s | code=%(app_code)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
                file_handler.setFormatter(formatter)
                if ErrorHandler._logger:
                    ErrorHandler._logger.addHandler(file_handler)

                # Console handler for debug builds
                if __debug__:
                    console_handler = logging.StreamHandler()
                    console_handler.setFormatter(formatter)
                    console_handler.setLevel(logging.WARNING)  # Only warnings and errors to console
                    if ErrorHandler._logger:
                        ErrorHandler._logger.addHandler(console_handler)

        except Exception as e:
            # Fallback to basic logging if setup fails
            logging.basicConfig(level=logging.ERROR)
            logging.error(f"Failed to setup error logging: {e}")

    def _sanitize_context(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Sanitize context to prevent sensitive data leakage.

        Args:
            context: Raw context dictionary

        Returns:
            Sanitized context dictionary
        """
        safe_context = {}

        # Limit context size
        max_items = 20
        item_count = 0

        for item_count, (key, value) in enumerate(context.items()):
            if item_count >= max_items:
                safe_context["..."] = f"({len(context) - max_items} more items truncated)"
                break

            # Skip sensitive keys
            if any(sensitive in key.lower() for sensitive in ["password", "token", "key", "secret"]):
                safe_context[key] = "[REDACTED]"
            else:
                # Safely represent the value
                try:
                    # Limit string length
                    if isinstance(value, str) and len(value) > 200:
                        safe_context[key] = value[:200] + "..."
                    else:
                        safe_context[key] = repr(value)[:200]
                except Exception:
                    safe_context[key] = "[REPR_FAILED]"

        return safe_context

    def install_hooks(self) -> None:
        """Install exception hooks for unhandled exceptions."""

        # Install sys.excepthook
        def exception_hook(exc_type: type[BaseException], exc_value: BaseException, exc_traceback: Any) -> None:
            """Handle unhandled exceptions."""
            if issubclass(exc_type, KeyboardInterrupt):
                # Let keyboard interrupts through
                self._original_excepthook(exc_type, exc_value, exc_traceback)
                return

            # Handle the exception
            try:
                if isinstance(exc_value, Exception):
                    self.handle(exc_value, {"source": "sys.excepthook"})
            except Exception:
                # Fallback to original handler if our handler fails
                self._original_excepthook(exc_type, exc_value, exc_traceback)

        sys.excepthook = exception_hook

        # Install threading.excepthook (Python 3.8+)
        if hasattr(threading, "excepthook"):

            def threading_exception_hook(args: threading.ExceptHookArgs) -> None:
                """Handle unhandled exceptions in threads."""
                try:
                    if isinstance(args.exc_value, Exception):
                        self.handle(
                            args.exc_value,
                            {
                                "source": "threading.excepthook",
                                "thread": args.thread.name if args.thread else "unknown",
                            },
                        )
                except Exception:
                    # Fallback to original handler
                    if self._original_threading_excepthook:
                        self._original_threading_excepthook(args)

            threading.excepthook = threading_exception_hook

    def restore_hooks(self) -> None:
        """Restore original exception hooks."""
        sys.excepthook = self._original_excepthook
        if self._original_threading_excepthook:
            threading.excepthook = self._original_threading_excepthook


# Global instance accessor
_error_handler_instance: ErrorHandler | None = None


def get_error_handler() -> ErrorHandler:
    """
    Get the global ErrorHandler instance.

    Returns:
        The singleton ErrorHandler instance
    """
    # Use the same singleton mechanism as the class
    return ErrorHandler()


def setup_error_handling() -> ErrorHandler:
    """
    Set up global error handling for the application.

    This should be called once during application startup.

    Returns:
        The configured ErrorHandler instance
    """
    handler = get_error_handler()
    handler.install_hooks()
    return handler


def init_logging() -> None:
    """
    Initialize logging configuration.

    This sets up the basic logging infrastructure and should be called
    early in application startup.
    """
    # The ErrorHandler will set up its own logging when instantiated
    get_error_handler()

    # Set up basic logging for other modules
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
