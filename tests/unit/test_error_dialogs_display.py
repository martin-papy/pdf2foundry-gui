"""
Tests for ErrorDialogManager display functionality.

Tests cover:
- Error dialog display with recovery actions
- Main thread dialog handling
- Icon mapping based on error severity
"""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from core.errors import ErrorCode, ErrorSeverity, FileError
from gui.dialogs.error_dialogs import ErrorDialogManager, RecoveryAction


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Create QApplication for all tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestErrorDialogDisplay:
    """Test error dialog display functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = ErrorDialogManager()

    def test_show_error_basic(self):
        """Test basic error dialog display."""
        error = FileError(
            code=ErrorCode.FILE_NOT_FOUND,
            user_message="File not found",
            file_path="/test/path",
        )
        with patch.object(self.manager, "_show_error_main_thread") as mock_show:
            mock_show.return_value = RecoveryAction.CANCEL
            result = self.manager.show_error(error)
            assert result == RecoveryAction.CANCEL
            mock_show.assert_called_once_with(error, [])

    def test_show_error_with_actions(self):
        """Test error dialog display with recovery actions."""
        error = FileError(
            code=ErrorCode.FILE_NOT_FOUND,
            user_message="File not found",
            file_path="/test/path",
        )
        actions = [RecoveryAction.RETRY, RecoveryAction.SELECT_ALTERNATIVE_PATH]
        with patch.object(self.manager, "_show_error_main_thread") as mock_show:
            mock_show.return_value = RecoveryAction.RETRY
            result = self.manager.show_error(error, actions)
            assert result == RecoveryAction.RETRY
            mock_show.assert_called_once_with(error, actions)

    def test_show_error_with_parent(self):
        """Test error dialog display with parent widget."""
        parent = QWidget()
        manager = ErrorDialogManager(parent)
        error = FileError(
            code=ErrorCode.FILE_NOT_FOUND,
            user_message="File not found",
            file_path="/test/path",
        )
        with patch.object(manager, "_show_error_main_thread") as mock_show:
            mock_show.return_value = RecoveryAction.CANCEL
            result = manager.show_error(error)
            assert result == RecoveryAction.CANCEL

    @patch("gui.dialogs.error_dialogs.QApplication.instance")
    @patch("gui.dialogs.error_dialogs.QThread.currentThread")
    def test_show_error_from_different_thread(self, mock_current_thread, mock_app_instance):
        """Test error dialog display from different thread."""
        mock_app = Mock()
        mock_app_instance.return_value = mock_app
        mock_main_thread = Mock()
        mock_app.thread.return_value = mock_main_thread
        mock_current_thread.return_value = Mock()  # Different thread

        error = FileError(
            code=ErrorCode.FILE_NOT_FOUND,
            user_message="File not found",
            file_path="/test/path",
        )
        with patch.object(self.manager, "_show_error_main_thread") as mock_show:
            mock_show.return_value = RecoveryAction.CANCEL
            result = self.manager.show_error(error)
            assert result == RecoveryAction.CANCEL


class TestErrorDialogMainThread:
    """Test error dialog display in main thread."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = ErrorDialogManager()
        self.error = FileError(
            code=ErrorCode.FILE_NOT_FOUND,
            user_message="Test error message",
            file_path="/test/path",
        )

    @patch("gui.dialogs.error_dialogs.to_user_error")
    @patch("gui.dialogs.error_dialogs.QMessageBox")
    def test_show_error_main_thread_basic(self, mock_message_box, mock_to_user_error):
        """Test basic error dialog in main thread."""
        mock_to_user_error.return_value = ("User Error", "User message", "Technical details")
        mock_box = Mock()
        mock_message_box.return_value = mock_box
        mock_box.exec.return_value = QMessageBox.StandardButton.Cancel

        result = self.manager._show_error_main_thread(self.error, [])

        assert result == RecoveryAction.CANCEL
        mock_message_box.assert_called_once()
        mock_box.setWindowTitle.assert_called_with("User Error")
        mock_box.setText.assert_called_with("User message")
        mock_box.setIcon.assert_called_with(QMessageBox.Icon.Critical)

    @patch("gui.dialogs.error_dialogs.to_user_error")
    @patch("gui.dialogs.error_dialogs.QMessageBox")
    def test_show_error_main_thread_with_details(self, mock_message_box, mock_to_user_error):
        """Test error dialog with detailed information."""
        mock_to_user_error.return_value = ("User Error", "User message", "Technical details")
        mock_box = Mock()
        mock_message_box.return_value = mock_box
        mock_box.exec.return_value = QMessageBox.StandardButton.Cancel

        result = self.manager._show_error_main_thread(self.error, [])

        assert result == RecoveryAction.CANCEL
        mock_box.setDetailedText.assert_called_with("Technical details")

    def test_show_error_main_thread_icon_mapping(self):
        """Test error severity to icon mapping."""
        test_cases = [
            (ErrorSeverity.LOW, QMessageBox.Icon.Information),
            (ErrorSeverity.MEDIUM, QMessageBox.Icon.Warning),
            (ErrorSeverity.HIGH, QMessageBox.Icon.Critical),
            (ErrorSeverity.CRITICAL, QMessageBox.Icon.Critical),
        ]

        for severity, expected_icon in test_cases:
            with (
                patch("gui.dialogs.error_dialogs.to_user_error") as mock_to_user_error,
                patch("gui.dialogs.error_dialogs.QMessageBox") as mock_message_box,
            ):
                mock_to_user_error.return_value = ("Title", "Message", "Details")
                mock_box = Mock()
                mock_message_box.return_value = mock_box
                mock_box.exec.return_value = QMessageBox.StandardButton.Cancel

                error = FileError(
                    code=ErrorCode.FILE_NOT_FOUND,
                    user_message="Test error",
                    file_path="/test/path",
                    severity=severity,
                )

                self.manager._show_error_main_thread(error, [])
                mock_box.setIcon.assert_called_with(expected_icon)
