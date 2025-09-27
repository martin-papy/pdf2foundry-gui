"""
Tests for RecoveryManager initialization and basic functionality.
"""

from unittest.mock import patch

from PySide6.QtCore import QObject, QTimer

from core.conversion_config import ConversionConfig
from core.errors import ErrorCode, FileError
from gui.dialogs.error_dialogs import RecoveryAction
from gui.recovery_manager import RecoveryManager


class TestRecoveryManagerInitialization:
    """Test RecoveryManager initialization and setup."""

    def test_initialization_basic(self):
        """Test basic initialization."""
        manager = RecoveryManager()
        assert manager._attempt_count == 0
        assert manager._max_attempts == 3
        assert manager._base_backoff_ms == 1000
        assert manager._max_backoff_ms == 30000
        assert manager._in_recovery is False
        assert manager._current_job_id is None
        assert manager._current_config is None

    def test_initialization_with_parent(self):
        """Test initialization with parent object."""
        parent = QObject()
        manager = RecoveryManager(parent)
        assert manager.parent() is parent

    def test_signals_exist(self):
        """Test that required signals exist."""
        manager = RecoveryManager()
        assert hasattr(manager, "recoveryRequested")
        assert hasattr(manager, "performRetryRequested")
        assert hasattr(manager, "cancelRequested")
        assert hasattr(manager, "alternativePathSelected")
        assert hasattr(manager, "settingsRequested")
        assert hasattr(manager, "issueReportRequested")

    def test_retry_timer_setup(self):
        """Test retry timer setup."""
        manager = RecoveryManager()
        assert isinstance(manager._retry_timer, QTimer)
        assert manager._retry_timer.isSingleShot()

    def test_error_dialog_manager_setup(self):
        """Test error dialog manager setup."""
        manager = RecoveryManager()
        assert manager._error_dialog_manager is not None

    def test_logger_setup(self):
        """Test logger setup."""
        manager = RecoveryManager()
        assert manager._logger is not None


class TestRecoveryStateQueries:
    """Test recovery state query methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = RecoveryManager()

    def test_can_retry_within_limit(self):
        """Test retry capability within attempt limit."""
        self.manager._attempt_count = 2
        assert self.manager.can_retry() is True

    def test_can_retry_at_limit(self):
        """Test retry capability at attempt limit."""
        self.manager._attempt_count = 3
        assert self.manager.can_retry() is False

    def test_can_retry_over_limit(self):
        """Test retry capability over attempt limit."""
        self.manager._attempt_count = 5
        assert self.manager.can_retry() is False

    def test_is_in_recovery_initial_state(self):
        """Test initial recovery state."""
        assert self.manager._in_recovery is False

    def test_is_in_recovery_after_start(self):
        """Test recovery state after starting recovery."""
        error = FileError(
            code=ErrorCode.FILE_NOT_FOUND,
            user_message="File not found",
            file_path="/test/file.pdf",
        )
        config = ConversionConfig(
            pdf_file="/test/file.pdf",
            mod_id="test-mod",
            mod_title="Test Module",
            output_directory="/test/output",
        )

        with patch.object(self.manager._error_dialog_manager, "show_error") as mock_show:
            mock_show.return_value = RecoveryAction.CANCEL
            self.manager.start_recovery("job123", error, config)
            assert self.manager._in_recovery is True


class TestRecoveryReset:
    """Test recovery state reset functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = RecoveryManager()

    def test_reset_recovery_state(self):
        """Test recovery state reset."""
        config = ConversionConfig(
            pdf_file="/test/file.pdf",
            mod_id="test-mod",
            mod_title="Test Module",
            output_directory="/test/output",
        )

        self.manager._in_recovery = True
        self.manager._current_job_id = "job123"
        self.manager._current_config = config
        self.manager._attempt_count = 2

        self.manager.reset_recovery_state()

        assert self.manager._in_recovery is False
        assert self.manager._current_job_id is None
        assert self.manager._current_config is None
        assert self.manager._attempt_count == 0

    def test_reset_recovery_state_idempotent(self):
        """Test that reset is idempotent."""
        self.manager.reset_recovery_state()
        self.manager.reset_recovery_state()  # Should not raise exception

        assert self.manager._in_recovery is False
        assert self.manager._current_job_id is None
        assert self.manager._current_config is None
        assert self.manager._attempt_count == 0


class TestRecoveryConfiguration:
    """Test recovery configuration parameters."""

    def test_default_max_attempts(self):
        """Test default maximum attempts."""
        manager = RecoveryManager()
        assert manager._max_attempts == 3

    def test_custom_max_attempts(self):
        """Test custom maximum attempts configuration."""
        manager = RecoveryManager()
        manager._max_attempts = 5

        manager._attempt_count = 4
        assert manager.can_retry() is True

        manager._attempt_count = 5
        assert manager.can_retry() is False

    def test_default_backoff_settings(self):
        """Test default backoff settings."""
        manager = RecoveryManager()
        assert manager._base_backoff_ms == 1000
        assert manager._max_backoff_ms == 30000

    def test_custom_backoff_settings(self):
        """Test custom backoff settings."""
        manager = RecoveryManager()
        manager._base_backoff_ms = 500
        manager._max_backoff_ms = 10000

        assert manager._calculate_backoff(1) == 500
        assert manager._calculate_backoff(2) == 1000
        assert manager._calculate_backoff(10) == 10000  # Should cap at max
