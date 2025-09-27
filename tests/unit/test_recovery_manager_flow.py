"""
Tests for RecoveryManager recovery flow and coordination.
"""

from unittest.mock import patch

from core.conversion_config import ConversionConfig
from core.errors import ErrorCode, FileError, SystemError
from gui.dialogs.error_dialogs import RecoveryAction
from gui.recovery_manager import RecoveryManager


class TestRecoveryStart:
    """Test recovery start functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = RecoveryManager()
        self.config = ConversionConfig(
            pdf_file="/test/file.pdf",
            mod_id="test-mod",
            mod_title="Test Module",
            output_directory="/test/output",
        )
        self.error = FileError(
            code=ErrorCode.FILE_NOT_FOUND,
            user_message="File not found",
            file_path="/test/file.pdf",
        )

    def test_start_recovery_basic(self):
        """Test basic recovery start."""
        with patch.object(self.manager._error_dialog_manager, "show_error") as mock_show:
            mock_show.return_value = RecoveryAction.CANCEL

            result = self.manager.start_recovery("job123", self.error, self.config)

            assert result == RecoveryAction.CANCEL
            assert self.manager._in_recovery is True
            assert self.manager._current_job_id == "job123"
            assert self.manager._current_config is self.config
            mock_show.assert_called_once()

    def test_start_recovery_already_in_recovery(self):
        """Test starting recovery when already in recovery."""
        self.manager._in_recovery = True

        with patch.object(self.manager._logger, "warning") as mock_log:
            result = self.manager.start_recovery("job123", self.error, self.config)

            assert result == RecoveryAction.CANCEL
            mock_log.assert_called_once()

    def test_start_recovery_with_retry_action(self):
        """Test recovery start with retry action."""
        with patch.object(self.manager._error_dialog_manager, "show_error") as mock_show:
            mock_show.return_value = RecoveryAction.RETRY

            result = self.manager.start_recovery("job123", self.error, self.config)

            assert result == RecoveryAction.RETRY
            assert self.manager._attempt_count == 1

    def test_start_recovery_with_alternative_path_action(self):
        """Test recovery start with alternative path action."""
        with patch.object(self.manager._error_dialog_manager, "show_error") as mock_show:
            mock_show.return_value = RecoveryAction.SELECT_ALTERNATIVE_PATH

            result = self.manager.start_recovery("job123", self.error, self.config)

            assert result == RecoveryAction.SELECT_ALTERNATIVE_PATH

    def test_start_recovery_emits_signal(self):
        """Test that recovery start emits appropriate signal."""
        signal_emitted = False
        received_job_id = None
        received_error = None
        received_config = None

        def on_recovery_requested(job_id, error, config):
            nonlocal signal_emitted, received_job_id, received_error, received_config
            signal_emitted = True
            received_job_id = job_id
            received_error = error
            received_config = config

        self.manager.recoveryRequested.connect(on_recovery_requested)

        with patch.object(self.manager._error_dialog_manager, "show_error") as mock_show:
            mock_show.return_value = RecoveryAction.CANCEL
            self.manager.start_recovery("job123", self.error, self.config)

        assert signal_emitted
        assert received_job_id == "job123"
        assert received_error is self.error
        assert received_config is self.config


class TestConversionErrorHandling:
    """Test conversion error handling during recovery."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = RecoveryManager()
        self.config = ConversionConfig(
            pdf_file="/test/file.pdf",
            mod_id="test-mod",
            mod_title="Test Module",
            output_directory="/test/output",
        )

    def test_handle_file_not_found_error(self):
        """Test handling of file not found error."""
        error = FileError(
            code=ErrorCode.FILE_NOT_FOUND,
            user_message="File not found",
            file_path="/test/file.pdf",
        )

        with patch.object(self.manager._error_dialog_manager, "show_error") as mock_show:
            mock_show.return_value = RecoveryAction.SELECT_ALTERNATIVE_PATH

            result = self.manager.start_recovery("job123", error, self.config)

            assert result == RecoveryAction.SELECT_ALTERNATIVE_PATH
            mock_show.assert_called_once_with(error, [])

    def test_handle_permission_denied_error(self):
        """Test handling of permission denied error."""
        error = FileError(
            code=ErrorCode.FILE_PERMISSION_DENIED,
            user_message="Permission denied",
            file_path="/test/file.pdf",
        )

        with patch.object(self.manager._error_dialog_manager, "show_error") as mock_show:
            mock_show.return_value = RecoveryAction.OPEN_PERMISSIONS_HELP

            result = self.manager.start_recovery("job123", error, self.config)

            assert result == RecoveryAction.OPEN_PERMISSIONS_HELP

    def test_handle_validation_error(self):
        """Test handling of validation error."""
        from core.errors import ValidationError

        error = ValidationError(
            code=ErrorCode.VALIDATION_FAILED,
            user_message="Validation failed",
            field="test_field",
        )

        with patch.object(self.manager._error_dialog_manager, "show_error") as mock_show:
            mock_show.return_value = RecoveryAction.OPEN_SETTINGS

            result = self.manager.start_recovery("job123", error, self.config)

            assert result == RecoveryAction.OPEN_SETTINGS

    def test_handle_system_error(self):
        """Test handling of system error."""
        error = SystemError(
            code=ErrorCode.BACKEND_ERROR,
            user_message="System error",
            is_retriable=True,
        )

        with patch.object(self.manager._error_dialog_manager, "show_error") as mock_show:
            mock_show.return_value = RecoveryAction.RETRY

            result = self.manager.start_recovery("job123", error, self.config)

            assert result == RecoveryAction.RETRY
            assert self.manager._attempt_count == 1

    def test_handle_non_retriable_error(self):
        """Test handling of non-retriable error."""
        error = SystemError(
            code=ErrorCode.BACKEND_ERROR,
            user_message="System error",
            is_retriable=False,
        )

        with patch.object(self.manager._error_dialog_manager, "show_error") as mock_show:
            mock_show.return_value = RecoveryAction.CANCEL

            result = self.manager.start_recovery("job123", error, self.config)

            assert result == RecoveryAction.CANCEL

    def test_handle_critical_error(self):
        """Test handling of critical severity error."""
        from core.errors import ErrorSeverity

        error = SystemError(
            code=ErrorCode.BACKEND_ERROR,
            user_message="Critical system error",
            severity=ErrorSeverity.CRITICAL,
        )

        with patch.object(self.manager._error_dialog_manager, "show_error") as mock_show:
            mock_show.return_value = RecoveryAction.REPORT_ISSUE

            result = self.manager.start_recovery("job123", error, self.config)

            assert result == RecoveryAction.REPORT_ISSUE


class TestRecoveryCancellation:
    """Test recovery cancellation functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = RecoveryManager()

    def test_cancel_recovery_emits_signal(self):
        """Test that cancel recovery emits appropriate signal."""
        signal_emitted = False
        received_job_id = None

        def on_cancel_requested(job_id):
            nonlocal signal_emitted, received_job_id
            signal_emitted = True
            received_job_id = job_id

        self.manager.cancelRequested.connect(on_cancel_requested)
        self.manager._current_job_id = "job123"

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

        assert signal_emitted
        assert received_job_id == "job123"

    def test_cancel_without_current_job(self):
        """Test cancel behavior without current job."""
        signal_emitted = False

        def on_cancel_requested(job_id):
            nonlocal signal_emitted
            signal_emitted = True

        self.manager.cancelRequested.connect(on_cancel_requested)

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

        # Signal should still be emitted even if no current job was set initially
        assert signal_emitted
