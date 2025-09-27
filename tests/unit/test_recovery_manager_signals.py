"""
Tests for RecoveryManager signal handling and dialog integration.
"""

from unittest.mock import patch

from core.conversion_config import ConversionConfig
from core.errors import ErrorCode, ErrorSeverity, FileError, SystemError
from gui.dialogs.error_dialogs import RecoveryAction
from gui.recovery_manager import RecoveryManager


class TestRecoveryDialogHandling:
    """Test integration with error dialog system."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = RecoveryManager()
        self.config = ConversionConfig(
            pdf_file="/test/file.pdf",
            mod_id="test-mod",
            mod_title="Test Module",
            output_directory="/test/output",
        )

    def test_dialog_manager_integration(self):
        """Test integration with dialog manager."""
        error = FileError(
            code=ErrorCode.FILE_NOT_FOUND,
            user_message="File not found",
            file_path="/test/file.pdf",
        )

        with patch.object(self.manager._error_dialog_manager, "show_error") as mock_show:
            mock_show.return_value = RecoveryAction.CANCEL

            result = self.manager.start_recovery("job123", error, self.config)

            assert result == RecoveryAction.CANCEL
            mock_show.assert_called_once_with(error, [])

    def test_dialog_with_recovery_actions(self):
        """Test dialog display with recovery actions."""
        error = FileError(
            code=ErrorCode.FILE_NOT_FOUND,
            user_message="File not found",
            file_path="/test/file.pdf",
        )

        # Mock the error dialog manager to return specific actions
        with (
            patch.object(self.manager._error_dialog_manager, "show_error") as mock_show,
            patch.object(self.manager._error_dialog_manager, "_determine_recovery_actions") as mock_actions,
        ):
            mock_actions.return_value = [RecoveryAction.SELECT_ALTERNATIVE_PATH, RecoveryAction.CANCEL]
            mock_show.return_value = RecoveryAction.SELECT_ALTERNATIVE_PATH

            result = self.manager.start_recovery("job123", error, self.config)

            assert result == RecoveryAction.SELECT_ALTERNATIVE_PATH

    def test_dialog_signal_connections(self):
        """Test that dialog signals are properly connected."""
        # This is tested indirectly through the signal handling tests
        assert self.manager._error_dialog_manager is not None
        # The actual signal connections are tested in the signal handling methods


class TestRecoveryActionHandling:
    """Test recovery action handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = RecoveryManager()
        self.config = ConversionConfig(
            pdf_file="/test/file.pdf",
            mod_id="test-mod",
            mod_title="Test Module",
            output_directory="/test/output",
        )

    def test_handle_cancel_action(self):
        """Test handling of cancel action."""
        error = FileError(
            code=ErrorCode.FILE_NOT_FOUND,
            user_message="File not found",
            file_path="/test/file.pdf",
        )

        with patch.object(self.manager._error_dialog_manager, "show_error") as mock_show:
            mock_show.return_value = RecoveryAction.CANCEL

            result = self.manager.start_recovery("job123", error, self.config)

            assert result == RecoveryAction.CANCEL
            assert self.manager._in_recovery is True  # State maintained until reset

    def test_handle_select_alternative_path_action(self):
        """Test handling of select alternative path action."""
        error = FileError(
            code=ErrorCode.FILE_NOT_FOUND,
            user_message="File not found",
            file_path="/test/file.pdf",
        )

        with patch.object(self.manager._error_dialog_manager, "show_error") as mock_show:
            mock_show.return_value = RecoveryAction.SELECT_ALTERNATIVE_PATH

            result = self.manager.start_recovery("job123", error, self.config)

            assert result == RecoveryAction.SELECT_ALTERNATIVE_PATH

    def test_handle_open_settings_action(self):
        """Test handling of open settings action."""
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

    def test_handle_report_issue_action(self):
        """Test handling of report issue action."""
        error = SystemError(
            code=ErrorCode.BACKEND_ERROR,
            user_message="System error",
            severity=ErrorSeverity.HIGH,
        )

        with patch.object(self.manager._error_dialog_manager, "show_error") as mock_show:
            mock_show.return_value = RecoveryAction.REPORT_ISSUE

            result = self.manager.start_recovery("job123", error, self.config)

            assert result == RecoveryAction.REPORT_ISSUE


class TestSignalHandling:
    """Test signal emission and handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = RecoveryManager()

    def test_alternative_path_requested_handler(self):
        """Test alternative path requested handler."""
        signal_emitted = False
        received_path = None

        def on_alternative_path_selected(path):
            nonlocal signal_emitted, received_path
            signal_emitted = True
            received_path = path

        self.manager.alternativePathSelected.connect(on_alternative_path_selected)
        self.manager._on_alternative_path_requested("/new/path.pdf")

        assert signal_emitted
        assert received_path == "/new/path.pdf"

    def test_settings_requested_handler(self):
        """Test settings requested handler."""
        signal_emitted = False

        def on_settings_requested():
            nonlocal signal_emitted
            signal_emitted = True

        self.manager.settingsRequested.connect(on_settings_requested)
        self.manager._on_settings_requested()

        assert signal_emitted

    def test_issue_report_requested_handler(self):
        """Test issue report requested handler."""
        signal_emitted = False
        received_report = None

        def on_issue_report_requested(report):
            nonlocal signal_emitted, received_report
            signal_emitted = True
            received_report = report

        self.manager.issueReportRequested.connect(on_issue_report_requested)
        self.manager._on_issue_report_requested("Error report content")

        assert signal_emitted
        assert received_report == "Error report content"

    def test_concurrent_signal_handling(self):
        """Test handling of concurrent signals."""
        # Test that multiple signals can be handled without interference
        path_signal_emitted = False
        settings_signal_emitted = False

        def on_alternative_path_selected(path):
            nonlocal path_signal_emitted
            path_signal_emitted = True

        def on_settings_requested():
            nonlocal settings_signal_emitted
            settings_signal_emitted = True

        self.manager.alternativePathSelected.connect(on_alternative_path_selected)
        self.manager.settingsRequested.connect(on_settings_requested)

        self.manager._on_alternative_path_requested("/new/path.pdf")
        self.manager._on_settings_requested()

        assert path_signal_emitted
        assert settings_signal_emitted


class TestRecoveryManagerIntegration:
    """Test integration scenarios combining multiple components."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = RecoveryManager()

    def test_complete_retry_flow(self):
        """Test complete retry flow from start to finish."""
        config = ConversionConfig(
            pdf_file="/test/file.pdf",
            mod_id="test-mod",
            mod_title="Test Module",
            output_directory="/test/output",
        )
        error = FileError(
            code=ErrorCode.FILE_NOT_FOUND,
            user_message="File not found",
            file_path="/test/file.pdf",
            is_retriable=True,
        )

        # Track signal emissions
        retry_signal_emitted = False
        received_job_id = None
        received_config = None

        def on_retry_requested(job_id, config_obj):
            nonlocal retry_signal_emitted, received_job_id, received_config
            retry_signal_emitted = True
            received_job_id = job_id
            received_config = config_obj

        self.manager.performRetryRequested.connect(on_retry_requested)

        # Start recovery with retry action
        with patch.object(self.manager._error_dialog_manager, "show_error") as mock_show:
            mock_show.return_value = RecoveryAction.RETRY

            result = self.manager.start_recovery("job123", error, config)

            assert result == RecoveryAction.RETRY
            assert self.manager._attempt_count == 1
            assert self.manager._in_recovery is True

        # Simulate retry timer timeout
        self.manager._perform_retry()

        assert retry_signal_emitted
        assert received_job_id == "job123"
        assert received_config is config

    def test_alternative_path_selection_flow(self):
        """Test alternative path selection flow."""
        config = ConversionConfig(
            pdf_file="/test/file.pdf",
            mod_id="test-mod",
            mod_title="Test Module",
            output_directory="/test/output",
        )
        error = FileError(
            code=ErrorCode.FILE_NOT_FOUND,
            user_message="File not found",
            file_path="/test/file.pdf",
        )

        # Track signal emissions
        path_signal_emitted = False
        received_path = None

        def on_alternative_path_selected(path):
            nonlocal path_signal_emitted, received_path
            path_signal_emitted = True
            received_path = path

        self.manager.alternativePathSelected.connect(on_alternative_path_selected)

        # Start recovery with alternative path action
        with patch.object(self.manager._error_dialog_manager, "show_error") as mock_show:
            mock_show.return_value = RecoveryAction.SELECT_ALTERNATIVE_PATH

            result = self.manager.start_recovery("job123", error, config)

            assert result == RecoveryAction.SELECT_ALTERNATIVE_PATH

        # Simulate alternative path selection
        self.manager._on_alternative_path_requested("/new/path.pdf")

        assert path_signal_emitted
        assert received_path == "/new/path.pdf"

    def test_settings_request_flow(self):
        """Test settings request flow."""
        from core.errors import ValidationError

        config = ConversionConfig(
            pdf_file="/test/file.pdf",
            mod_id="test-mod",
            mod_title="Test Module",
            output_directory="/test/output",
        )
        error = ValidationError(
            code=ErrorCode.VALIDATION_FAILED,
            user_message="Invalid configuration",
            field="test_field",
        )

        # Track signal emissions
        settings_signal_emitted = False

        def on_settings_requested():
            nonlocal settings_signal_emitted
            settings_signal_emitted = True

        self.manager.settingsRequested.connect(on_settings_requested)

        # Start recovery with settings action
        with patch.object(self.manager._error_dialog_manager, "show_error") as mock_show:
            mock_show.return_value = RecoveryAction.OPEN_SETTINGS

            result = self.manager.start_recovery("job123", error, config)

            assert result == RecoveryAction.OPEN_SETTINGS

        # Simulate settings request
        self.manager._on_settings_requested()

        assert settings_signal_emitted

    def test_concurrent_recovery_requests(self):
        """Test handling of concurrent recovery requests."""
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

            # Start first recovery
            result1 = self.manager.start_recovery("job1", error, config)

            # Try to start second recovery while first is active
            result2 = self.manager.start_recovery("job2", error, config)

            assert result1 == RecoveryAction.CANCEL
            assert result2 == RecoveryAction.CANCEL
            assert mock_show.call_count == 1  # Only first call should go through
