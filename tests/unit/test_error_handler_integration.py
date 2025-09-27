"""
Tests for ErrorHandler integration scenarios and thread safety.

Tests cover:
- Thread-safe error handling
- Exception hook installation
- Realistic integration scenarios
"""

import sys
import threading
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QApplication

from core.error_handler import ErrorHandler, get_error_handler, setup_error_handling
from core.errors import BaseAppError, ErrorCode, ErrorType


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Create QApplication for all tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestExceptionHooks:
    """Test exception hook installation and handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = ErrorHandler()
        self.original_hook = sys.excepthook

    def teardown_method(self):
        """Clean up test fixtures."""
        sys.excepthook = self.original_hook

    def test_install_hooks(self):
        """Test exception hook installation."""
        original_hook = sys.excepthook

        self.handler.install_hooks()

        # Hook should be replaced
        assert sys.excepthook != original_hook

    def test_exception_hook_handling(self):
        """Test that exception hook properly handles exceptions."""
        signal_received = False
        received_error = None

        def signal_handler(error):
            nonlocal signal_received, received_error
            signal_received = True
            received_error = error

        self.handler.errorOccurred.connect(signal_handler)
        self.handler.install_hooks()

        # Simulate an unhandled exception
        try:
            raise ValueError("Unhandled exception")
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            sys.excepthook(exc_type, exc_value, exc_traceback)

        # Process Qt events to ensure signal delivery
        if QApplication.instance():
            QApplication.processEvents()

        assert signal_received
        assert isinstance(received_error, BaseAppError)
        assert "Unhandled exception" in received_error.user_message

    def test_hook_preserves_original_behavior(self):
        """Test that hook preserves original exception behavior."""
        original_called = False

        def mock_original_hook(*args):
            nonlocal original_called
            original_called = True

        sys.excepthook = mock_original_hook
        self.handler.install_hooks()

        # Simulate an exception
        try:
            raise ValueError("Test exception")
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            sys.excepthook(exc_type, exc_value, exc_traceback)

        # Original hook should still be called
        assert original_called


class TestThreadSafety:
    """Test thread-safe error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = ErrorHandler()

    def test_signal_emission_from_different_thread(self):
        """Test that signals can be emitted from different threads."""
        signal_received = False
        received_error = None

        def signal_handler(error):
            nonlocal signal_received, received_error
            signal_received = True
            received_error = error

        self.handler.errorOccurred.connect(signal_handler)

        def thread_function():
            exception = ValueError("Thread error")
            self.handler.handle(exception)

        thread = threading.Thread(target=thread_function)
        thread.start()
        thread.join()

        # Process Qt events to ensure signal delivery
        if QApplication.instance():
            QApplication.processEvents()

        # Signal should be received (Qt handles thread safety)
        assert signal_received
        assert isinstance(received_error, BaseAppError)


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = ErrorHandler()

    def test_file_operation_error_flow(self):
        """Test complete error flow for file operation failure."""
        # Simulate file operation error
        original_exception = PermissionError("Access denied to /protected/file.pdf")
        context = {"operation": "read", "file_path": "/protected/file.pdf"}

        with patch.object(self.handler, "_logger") as mock_logger:
            app_error = self.handler.handle(original_exception, context)

            # Verify error properties
            assert app_error.type == ErrorType.FILE
            assert app_error.code == ErrorCode.PERMISSION_DENIED
            assert "Access denied" in app_error.user_message
            # Context values are sanitized with repr(), so strings get quotes
            assert app_error.context["operation"] == "'read'"
            assert app_error.context["file_path"] == "'/protected/file.pdf'"

            # Verify logging
            assert mock_logger.error.called

    def test_conversion_error_flow(self):
        """Test complete error flow for conversion failure."""
        # Create a conversion-specific error
        original_exception = RuntimeError("PDF conversion failed: corrupt file")
        context = {"pdf_path": "/test/corrupt.pdf", "page_count": 10}

        with patch.object(self.handler, "_logger") as mock_logger:
            app_error = self.handler.handle(original_exception, context)

            # Verify error properties
            assert app_error.type == ErrorType.SYSTEM
            assert app_error.code == ErrorCode.BACKEND_ERROR
            assert "conversion failed" in app_error.user_message.lower()

            # Verify logging
            assert mock_logger.error.called

    def test_setup_error_handling_integration(self):
        """Test complete setup_error_handling integration."""
        with patch.object(ErrorHandler, "install_hooks") as mock_install:
            handler = setup_error_handling()

            assert isinstance(handler, ErrorHandler)
            assert mock_install.called
            assert handler is get_error_handler()  # Should be singleton
