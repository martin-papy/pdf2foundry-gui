"""
Tests for ErrorDialogManager recovery action functionality.

Tests cover:
- Recovery action determination logic
- Action button creation and configuration
- Recovery action handling
- Signal emission for recovery actions
"""

import pytest
from PySide6.QtWidgets import QApplication

from core.errors import ErrorCode, ErrorSeverity, FileError, SystemError
from gui.dialogs.error_dialogs import ErrorDialogManager, RecoveryAction


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Create QApplication for all tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestRecoveryActionDetermination:
    """Test recovery action determination logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = ErrorDialogManager()

    def test_determine_actions_retriable_error(self):
        """Test action determination for retriable errors."""
        error = SystemError(
            code=ErrorCode.BACKEND_UNAVAILABLE,
            user_message="Backend unavailable",
            is_retriable=True,
        )
        actions = self.manager._determine_recovery_actions(error)
        assert RecoveryAction.RETRY in actions
        assert RecoveryAction.CANCEL in actions

    def test_determine_actions_file_permission_error(self):
        """Test action determination for file permission errors."""
        error = FileError(
            code=ErrorCode.FILE_PERMISSION_DENIED,
            user_message="Permission denied",
            file_path="/test/path",
        )
        actions = self.manager._determine_recovery_actions(error)
        assert RecoveryAction.OPEN_PERMISSIONS_HELP in actions
        assert RecoveryAction.CANCEL in actions

    def test_determine_actions_file_not_found_error(self):
        """Test action determination for file not found errors."""
        error = FileError(
            code=ErrorCode.FILE_NOT_FOUND,
            user_message="File not found",
            file_path="/test/path",
        )
        actions = self.manager._determine_recovery_actions(error)
        assert RecoveryAction.SELECT_ALTERNATIVE_PATH in actions
        assert RecoveryAction.CANCEL in actions

    def test_determine_actions_validation_error(self):
        """Test action determination for validation errors."""
        from core.errors import ValidationError

        error = ValidationError(
            code=ErrorCode.VALIDATION_FAILED,
            user_message="Validation failed",
            field="test_field",
        )
        actions = self.manager._determine_recovery_actions(error)
        assert RecoveryAction.OPEN_SETTINGS in actions
        assert RecoveryAction.CANCEL in actions

    def test_determine_actions_config_error(self):
        """Test action determination for configuration errors."""
        from core.errors import ConfigError

        error = ConfigError(
            code=ErrorCode.CONFIG_INVALID,
            user_message="Invalid configuration",
        )
        actions = self.manager._determine_recovery_actions(error)
        assert RecoveryAction.OPEN_SETTINGS in actions
        assert RecoveryAction.CANCEL in actions

    def test_determine_actions_high_severity_error(self):
        """Test action determination for high severity errors."""
        error = SystemError(
            code=ErrorCode.BACKEND_ERROR,
            user_message="System error",
            severity=ErrorSeverity.HIGH,
        )
        actions = self.manager._determine_recovery_actions(error)
        assert RecoveryAction.REPORT_ISSUE in actions
        assert RecoveryAction.CANCEL in actions

    def test_determine_actions_critical_severity_error(self):
        """Test action determination for critical severity errors."""
        error = SystemError(
            code=ErrorCode.BACKEND_ERROR,
            user_message="Critical system error",
            severity=ErrorSeverity.CRITICAL,
        )
        actions = self.manager._determine_recovery_actions(error)
        assert RecoveryAction.REPORT_ISSUE in actions
        assert RecoveryAction.CANCEL in actions

    def test_determine_actions_always_includes_cancel(self):
        """Test that cancel action is always included."""
        error = SystemError(
            code=ErrorCode.BACKEND_ERROR,
            user_message="Generic error",
        )
        actions = self.manager._determine_recovery_actions(error)
        assert RecoveryAction.CANCEL in actions
