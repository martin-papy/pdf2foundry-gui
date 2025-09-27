"""
Tests for ErrorDialogManager convenience functions and dialogs.

Tests cover:
- Warning dialogs
- Destructive action confirmation
- Status notifications
- Convenience functions
"""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox, QStatusBar, QWidget

from core.errors import ErrorCode, FileError
from gui.dialogs.error_dialogs import (
    ErrorDialogManager,
    RecoveryAction,
    confirm_destructive_action,
    show_error_dialog,
    show_warning_dialog,
)


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Create QApplication for all tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestWarningDialog:
    """Test warning dialog functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = ErrorDialogManager()

    @patch("gui.dialogs.error_dialogs.QMessageBox")
    def test_show_warning_ok(self, mock_message_box):
        """Test warning dialog with OK result."""
        mock_box = Mock()
        mock_message_box.return_value = mock_box
        mock_box.exec.return_value = QMessageBox.StandardButton.Ok

        result = self.manager.show_warning("Test Title", "Test Message")

        assert result is True
        mock_box.setWindowTitle.assert_called_with("Test Title")
        mock_box.setText.assert_called_with("Test Message")
        mock_box.setIcon.assert_called_with(QMessageBox.Icon.Warning)

    @patch("gui.dialogs.error_dialogs.QMessageBox")
    def test_show_warning_cancel(self, mock_message_box):
        """Test warning dialog with Cancel result."""
        mock_box = Mock()
        mock_message_box.return_value = mock_box
        mock_box.exec.return_value = QMessageBox.StandardButton.Cancel

        result = self.manager.show_warning("Test Title", "Test Message")
        assert result is False

    @patch("gui.dialogs.error_dialogs.QMessageBox")
    def test_show_warning_with_parent(self, mock_message_box):
        """Test warning dialog with parent widget."""
        parent = QWidget()
        manager = ErrorDialogManager(parent)
        mock_box = Mock()
        mock_message_box.return_value = mock_box
        mock_box.exec.return_value = QMessageBox.StandardButton.Ok

        result = manager.show_warning("Test Title", "Test Message")
        assert result is True


class TestConfirmDestructiveAction:
    """Test destructive action confirmation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = ErrorDialogManager()

    @patch("gui.dialogs.error_dialogs.QMessageBox")
    def test_confirm_destructive_action_yes(self, mock_message_box):
        """Test destructive action confirmation with Yes result."""
        mock_box = Mock()
        mock_message_box.return_value = mock_box
        mock_box.exec.return_value = QMessageBox.StandardButton.Yes

        result = self.manager.confirm_destructive_action("Delete File", "Are you sure you want to delete this file?")

        assert result is True
        mock_box.setWindowTitle.assert_called_with("Delete File")
        mock_box.setText.assert_called_with("Are you sure you want to delete this file?")
        mock_box.setIcon.assert_called_with(QMessageBox.Icon.Question)

    @patch("gui.dialogs.error_dialogs.QMessageBox")
    def test_confirm_destructive_action_cancel(self, mock_message_box):
        """Test destructive action confirmation with Cancel result."""
        mock_box = Mock()
        mock_message_box.return_value = mock_box
        mock_box.exec.return_value = QMessageBox.StandardButton.Cancel

        result = self.manager.confirm_destructive_action("Delete File", "Are you sure?")
        assert result is False


class TestStatusNotification:
    """Test status notification functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        parent = QWidget()
        parent.statusBar = Mock(return_value=Mock(spec=QStatusBar))
        self.manager = ErrorDialogManager(parent)

    def test_show_status_notification_with_status_bar(self):
        """Test status notification with status bar."""
        self.manager.show_status_notification("Test message", 5000)
        self.manager._status_bar.showMessage.assert_called_with("Test message", 5000)

    def test_show_status_notification_default_timeout(self):
        """Test status notification with default timeout."""
        self.manager.show_status_notification("Test message")
        self.manager._status_bar.showMessage.assert_called_with("Test message", 3000)

    def test_show_status_notification_without_status_bar(self):
        """Test status notification without status bar."""
        manager = ErrorDialogManager()
        # Should not raise exception
        manager.show_status_notification("Test message")


class TestConvenienceFunctions:
    """Test convenience functions."""

    @patch("gui.dialogs.error_dialogs.ErrorDialogManager")
    def test_show_error_dialog(self, mock_manager_class):
        """Test show_error_dialog convenience function."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.show_error.return_value = RecoveryAction.RETRY

        error = FileError(
            code=ErrorCode.FILE_NOT_FOUND,
            user_message="File not found",
            file_path="/test/path",
        )

        result = show_error_dialog(error)

        assert result == RecoveryAction.RETRY
        mock_manager.show_error.assert_called_once_with(error, None)

    @patch("gui.dialogs.error_dialogs.ErrorDialogManager")
    def test_show_warning_dialog(self, mock_manager_class):
        """Test show_warning_dialog convenience function."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.show_warning.return_value = True

        result = show_warning_dialog("Test Title", "Test Message")

        assert result is True
        mock_manager.show_warning.assert_called_once_with("Test Title", "Test Message")

    @patch("gui.dialogs.error_dialogs.ErrorDialogManager")
    def test_confirm_destructive_action(self, mock_manager_class):
        """Test confirm_destructive_action convenience function."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.confirm_destructive_action.return_value = True

        result = confirm_destructive_action("Delete File", "Are you sure?")

        assert result is True
        mock_manager.confirm_destructive_action.assert_called_once_with("Delete File", "Are you sure?")
