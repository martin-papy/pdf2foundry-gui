"""
Tests for ErrorHandler core functionality.

Tests cover:
- Singleton pattern behavior
- Exception capture and normalization
- Basic error handling
"""

from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QApplication

from core.error_handler import ErrorHandler, get_error_handler
from core.errors import BaseAppError, ErrorCode, ErrorType, FileError


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Create QApplication for all tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestErrorHandlerSingleton:
    """Test the singleton pattern implementation."""

    def test_singleton_pattern(self):
        """Test that ErrorHandler follows singleton pattern."""
        handler1 = ErrorHandler()
        handler2 = ErrorHandler()

        assert handler1 is handler2
        assert id(handler1) == id(handler2)

    def test_get_error_handler_returns_singleton(self):
        """Test that get_error_handler returns the singleton instance."""
        handler1 = get_error_handler()
        handler2 = get_error_handler()
        direct_handler = ErrorHandler()

        assert handler1 is handler2
        assert handler1 is direct_handler

    def test_initialization_only_once(self):
        """Test that initialization only happens once despite multiple instantiations."""
        # Clear any existing instance
        ErrorHandler._instance = None

        with patch.object(ErrorHandler, "_setup_logging") as mock_setup:
            handler1 = ErrorHandler()
            handler2 = ErrorHandler()

            # _setup_logging should only be called once
            assert mock_setup.call_count == 1
            assert handler1 is handler2


class TestErrorCapture:
    """Test exception capture and normalization."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = ErrorHandler()

    def test_capture_basic_exception(self):
        """Test capturing a basic exception."""
        original_exception = ValueError("Test error")

        app_error = self.handler.capture(original_exception)

        assert isinstance(app_error, BaseAppError)
        assert app_error.type == ErrorType.VALIDATION
        assert app_error.code == ErrorCode.INVALID_INPUT
        assert "Test error" in app_error.user_message
        assert "ValueError: Test error" in app_error.technical_message

    def test_capture_with_context(self):
        """Test capturing exception with context."""
        original_exception = FileNotFoundError("File not found")
        context = {"file_path": "/test/path", "operation": "read"}

        app_error = self.handler.capture(original_exception, context)

        assert isinstance(app_error, BaseAppError)
        assert app_error.type == ErrorType.FILE
        assert app_error.code == ErrorCode.FILE_NOT_FOUND
        assert "file_path" in app_error.context
        assert "operation" in app_error.context
        assert "traceback" in app_error.context

    def test_capture_already_app_error(self):
        """Test capturing an already normalized BaseAppError."""
        original_error = FileError(
            code=ErrorCode.PERMISSION_DENIED,
            user_message="Permission denied",
            file_path="/test/path",
        )

        app_error = self.handler.capture(original_error)

        # Should return the same error instance
        assert app_error is original_error
        assert app_error.code == ErrorCode.PERMISSION_DENIED

    def test_capture_with_sanitized_context(self):
        """Test that sensitive context is sanitized."""
        original_exception = ValueError("Test error")
        context = {
            "password": "secret123",
            "api_key": "key123",
            "token": "token123",
            "safe_data": "this is safe",
        }

        app_error = self.handler.capture(original_exception, context)

        assert app_error.context["password"] == "[REDACTED]"
        assert app_error.context["api_key"] == "[REDACTED]"
        assert app_error.context["token"] == "[REDACTED]"
        assert app_error.context["safe_data"] == "this is safe"
