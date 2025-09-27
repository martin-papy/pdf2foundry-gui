"""
Shared fixtures for RecoveryManager tests.
"""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtWidgets import QApplication

from core.conversion_config import ConversionConfig
from gui.dialogs.error_dialogs import RecoveryAction


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Create QApplication for all tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture(autouse=True)
def mock_error_dialog_manager():
    """Mock ErrorDialogManager to prevent actual dialogs from appearing during tests."""
    with patch("gui.recovery_manager.ErrorDialogManager") as mock_manager:
        mock_instance = Mock()
        mock_instance.show_error.return_value = RecoveryAction.CANCEL
        mock_instance.retryRequested = Mock()
        mock_instance.alternativePathRequested = Mock()
        mock_instance.settingsRequested = Mock()
        mock_instance.issueReportRequested = Mock()
        mock_manager.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def sample_config():
    """Sample conversion config for tests."""
    return ConversionConfig(
        pdf_file="/test/file.pdf",
        mod_id="test-mod",
        mod_title="Test Module",
        output_directory="/test/output",
    )
