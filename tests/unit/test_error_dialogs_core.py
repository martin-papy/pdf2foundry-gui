"""
Tests for core ErrorDialogManager functionality.

Tests cover:
- ErrorDialogManager initialization and setup
- RecoveryAction enum
- Basic error dialog display
"""

from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication, QStatusBar, QWidget

from gui.dialogs.error_dialogs import (
    ErrorDialogManager,
    RecoveryAction,
)


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Create QApplication for all tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestRecoveryAction:
    """Test the RecoveryAction enum."""

    def test_recovery_action_values(self):
        """Test that RecoveryAction enum has expected values."""
        assert RecoveryAction.RETRY.value == "retry"
        assert RecoveryAction.SELECT_ALTERNATIVE_PATH.value == "select_alternative_path"
        assert RecoveryAction.OPEN_PERMISSIONS_HELP.value == "open_permissions_help"
        assert RecoveryAction.OPEN_SETTINGS.value == "open_settings"
        assert RecoveryAction.REPORT_ISSUE.value == "report_issue"
        assert RecoveryAction.CANCEL.value == "cancel"


class TestErrorDialogManagerInitialization:
    """Test ErrorDialogManager initialization and setup."""

    def test_initialization_without_parent(self):
        """Test initialization without parent widget."""
        manager = ErrorDialogManager()
        assert manager._parent_widget is None
        assert manager._logger is not None
        assert manager._status_bar is None

    def test_initialization_with_parent(self):
        """Test initialization with parent widget."""
        parent = QWidget()
        manager = ErrorDialogManager(parent)
        assert manager._parent_widget is parent

    def test_initialization_with_status_bar_parent(self):
        """Test initialization with parent that has statusBar method."""
        parent = QWidget()
        parent.statusBar = Mock(return_value=Mock(spec=QStatusBar))
        manager = ErrorDialogManager(parent)
        assert manager._status_bar is not None

    def test_signals_exist(self):
        """Test that required signals exist."""
        manager = ErrorDialogManager()
        assert hasattr(manager, "retryRequested")
        assert hasattr(manager, "alternativePathRequested")
        assert hasattr(manager, "settingsRequested")
        assert hasattr(manager, "issueReportRequested")
