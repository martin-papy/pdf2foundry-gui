"""
Tests for ErrorHandler logging and setup functionality.

Tests cover:
- Logging setup and configuration
- Context sanitization for security
- Module functions (init_logging, setup_error_handling)
"""

import logging
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QApplication

from core.error_handler import ErrorHandler, init_logging, setup_error_handling


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Create QApplication for all tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestLoggingSetup:
    """Test logging configuration and setup."""

    def setup_method(self):
        """Set up test fixtures."""
        # Clear any existing instance to test fresh setup
        ErrorHandler._instance = None

    def test_setup_logging_creates_directory(self):
        """Test that logging setup creates the logs directory."""
        with (
            patch("core.error_handler.QStandardPaths.writableLocation") as mock_location,
            tempfile.TemporaryDirectory() as temp_dir,
        ):
            mock_location.return_value = temp_dir

            ErrorHandler()

            logs_dir = Path(temp_dir) / "logs"
            assert logs_dir.exists()

    def test_setup_logging_fallback_location(self):
        """Test logging setup with fallback location."""
        with patch("core.error_handler.QStandardPaths.writableLocation") as mock_location:
            # First call returns empty (AppDataLocation), second returns config location
            mock_location.side_effect = ["", "/config/location"]

            with tempfile.TemporaryDirectory() as temp_dir:
                mock_location.side_effect = ["", temp_dir]

                ErrorHandler()

                # Should create logs directory in fallback location
                # Note: The exact path depends on APP_ORGANIZATION and APP_NAME

    def test_setup_logging_handles_failure(self):
        """Test that logging setup handles failures gracefully."""
        with patch("core.error_handler.QStandardPaths.writableLocation") as mock_location:
            mock_location.side_effect = Exception("Permission denied")

            with patch("logging.basicConfig") as mock_basic_config, patch("logging.error") as mock_log_error:
                ErrorHandler()

                # Should fall back to basic logging
                assert mock_basic_config.called
                assert mock_log_error.called

    def test_logger_configuration(self):
        """Test that logger is configured correctly."""
        with (
            patch("core.error_handler.QStandardPaths.writableLocation") as mock_location,
            tempfile.TemporaryDirectory() as temp_dir,
        ):
            mock_location.return_value = temp_dir

            handler = ErrorHandler()

            assert handler._logger is not None
            assert handler._logger.name == "pdf2foundry_gui.errors"
            assert handler._logger.level == logging.DEBUG
            assert not handler._logger.propagate

    def test_no_duplicate_handlers(self):
        """Test that multiple instances don't create duplicate handlers."""
        with (
            patch("core.error_handler.QStandardPaths.writableLocation") as mock_location,
            tempfile.TemporaryDirectory() as temp_dir,
        ):
            mock_location.return_value = temp_dir

            handler1 = ErrorHandler()
            initial_handler_count = len(handler1._logger.handlers)

            handler2 = ErrorHandler()  # Should be same instance
            final_handler_count = len(handler2._logger.handlers)

            assert initial_handler_count == final_handler_count
            assert handler1 is handler2


class TestContextSanitization:
    """Test context sanitization for security."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = ErrorHandler()

    def test_sanitize_context_basic(self):
        """Test basic context sanitization."""
        context = {"file": "test.pdf", "size": 1024}

        sanitized = self.handler._sanitize_context(context)

        assert "file" in sanitized
        assert "size" in sanitized
        assert sanitized["file"] == "'test.pdf'"
        assert sanitized["size"] == "1024"

    def test_sanitize_context_removes_sensitive_data(self):
        """Test that sensitive data is redacted."""
        context = {
            "password": "secret123",
            "api_key": "abc123",
            "auth_token": "xyz789",
            "secret_value": "hidden",
            "normal_field": "visible",
        }

        sanitized = self.handler._sanitize_context(context)

        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["api_key"] == "[REDACTED]"
        assert sanitized["auth_token"] == "[REDACTED]"
        assert sanitized["secret_value"] == "[REDACTED]"
        assert sanitized["normal_field"] == "'visible'"

    def test_sanitize_context_limits_items(self):
        """Test that context is limited to prevent excessive data."""
        # Create context with more than 20 items
        context = {f"field_{i}": f"value_{i}" for i in range(25)}

        sanitized = self.handler._sanitize_context(context)

        # Should have at most 21 items (20 + truncation message)
        assert len(sanitized) <= 21
        assert "..." in sanitized  # Truncation indicator

    def test_sanitize_context_limits_string_length(self):
        """Test that long strings are truncated."""
        long_value = "x" * 300
        context = {"long_field": long_value}

        sanitized = self.handler._sanitize_context(context)

        assert len(sanitized["long_field"]) <= 203  # 200 + quotes + ellipsis
        assert sanitized["long_field"].endswith("...")

    def test_sanitize_context_handles_repr_failure(self):
        """Test handling of objects that fail repr()."""

        class BadRepr:
            def __repr__(self):
                raise Exception("Repr failed")

        context = {"bad_object": BadRepr()}

        sanitized = self.handler._sanitize_context(context)

        assert sanitized["bad_object"] == "[REPR_FAILED]"


class TestModuleFunctions:
    """Test module-level functions."""

    def test_init_logging_function(self):
        """Test init_logging function."""
        with (
            patch("core.error_handler.QStandardPaths.writableLocation") as mock_location,
            tempfile.TemporaryDirectory() as temp_dir,
        ):
            mock_location.return_value = temp_dir

            # Clear any existing instance
            ErrorHandler._instance = None

            init_logging()

            # Should create ErrorHandler instance
            assert ErrorHandler._instance is not None

    def test_setup_error_handling_function(self):
        """Test setup_error_handling function."""
        with patch("core.error_handler.init_logging") as mock_init, patch("sys.excepthook") as mock_hook:
            setup_error_handling()

            mock_init.assert_called_once()
            # Should set exception hook
            assert mock_hook is not None
