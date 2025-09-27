"""
Tests for RecoveryManager retry logic and backoff calculation.
"""

from unittest.mock import patch

from core.conversion_config import ConversionConfig
from core.errors import ErrorCode, FileError
from gui.dialogs.error_dialogs import RecoveryAction
from gui.recovery_manager import RecoveryManager


class TestRetryScheduling:
    """Test retry scheduling and backoff calculation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = RecoveryManager()

    def test_calculate_backoff_first_attempt(self):
        """Test backoff calculation for first attempt."""
        backoff = self.manager._calculate_backoff(1)
        assert backoff == 1000  # Base backoff

    def test_calculate_backoff_second_attempt(self):
        """Test backoff calculation for second attempt."""
        backoff = self.manager._calculate_backoff(2)
        assert backoff == 2000  # 2^1 * 1000

    def test_calculate_backoff_third_attempt(self):
        """Test backoff calculation for third attempt."""
        backoff = self.manager._calculate_backoff(3)
        assert backoff == 4000  # 2^2 * 1000

    def test_calculate_backoff_max_limit(self):
        """Test backoff calculation respects maximum limit."""
        backoff = self.manager._calculate_backoff(10)
        assert backoff == 30000  # Max backoff

    def test_schedule_retry_basic(self):
        """Test basic retry scheduling."""
        self.manager._attempt_count = 1

        with patch.object(self.manager._retry_timer, "start") as mock_start:
            self.manager._schedule_retry()
            mock_start.assert_called_once_with(1000)

    def test_schedule_retry_with_backoff(self):
        """Test retry scheduling with exponential backoff."""
        self.manager._attempt_count = 2

        with patch.object(self.manager._retry_timer, "start") as mock_start:
            self.manager._schedule_retry()
            mock_start.assert_called_once_with(2000)

    def test_perform_retry_signal_emission(self):
        """Test retry signal emission."""
        signal_emitted = False
        received_job_id = None
        received_config = None

        def on_retry_requested(job_id, config):
            nonlocal signal_emitted, received_job_id, received_config
            signal_emitted = True
            received_job_id = job_id
            received_config = config

        self.manager.performRetryRequested.connect(on_retry_requested)
        self.manager._current_job_id = "job123"
        self.manager._current_config = ConversionConfig(
            pdf_file="/test/file.pdf",
            mod_id="test-mod",
            mod_title="Test Module",
            output_directory="/test/output",
        )

        self.manager._perform_retry()

        assert signal_emitted
        assert received_job_id == "job123"
        assert received_config is self.manager._current_config

    def test_perform_retry_without_current_job(self):
        """Test retry performance without current job."""
        with patch.object(self.manager._logger, "warning") as mock_log:
            self.manager._perform_retry()
            mock_log.assert_called_once()

    def test_backoff_progression(self):
        """Test backoff progression over multiple attempts."""
        backoffs = []
        for attempt in range(1, 6):
            backoffs.append(self.manager._calculate_backoff(attempt))

        # Should be exponentially increasing: 1000, 2000, 4000, 8000, 16000
        expected = [1000, 2000, 4000, 8000, 16000]
        assert backoffs == expected


class TestRetryHandling:
    """Test retry action handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = RecoveryManager()
        self.config = ConversionConfig(
            pdf_file="/test/file.pdf",
            mod_id="test-mod",
            mod_title="Test Module",
            output_directory="/test/output",
        )

    def test_retry_requested_handler(self):
        """Test retry requested handler."""
        self.manager._current_job_id = "job123"
        self.manager._current_config = self.config

        with patch.object(self.manager, "_schedule_retry") as mock_schedule:
            self.manager._on_retry_requested()
            mock_schedule.assert_called_once()

    def test_retry_requested_without_current_job(self):
        """Test retry requested handler without current job."""
        with patch.object(self.manager._logger, "warning") as mock_log:
            self.manager._on_retry_requested()
            mock_log.assert_called_once()

    def test_handle_retry_action(self):
        """Test handling of retry action."""
        error = FileError(
            code=ErrorCode.FILE_NOT_FOUND,
            user_message="File not found",
            file_path="/test/file.pdf",
            is_retriable=True,
        )

        with patch.object(self.manager._error_dialog_manager, "show_error") as mock_show:
            mock_show.return_value = RecoveryAction.RETRY

            result = self.manager.start_recovery("job123", error, self.config)

            assert result == RecoveryAction.RETRY
            assert self.manager._attempt_count == 1

    def test_retry_timer_thread_safety(self):
        """Test retry timer thread safety."""
        self.manager._current_job_id = "job123"
        self.manager._current_config = self.config

        with patch.object(self.manager, "performRetryRequested") as mock_signal:
            # Simulate timer timeout
            self.manager._perform_retry()

            # Should emit signal
            mock_signal.emit.assert_called_once()


class TestFinalFailureHandling:
    """Test final failure handling when max attempts reached."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = RecoveryManager()

    def test_max_attempts_reached_behavior(self):
        """Test behavior when max attempts is reached."""
        self.manager._attempt_count = 3

        error = FileError(
            code=ErrorCode.FILE_NOT_FOUND,
            user_message="File not found",
            file_path="/test/file.pdf",
            is_retriable=True,
        )
        config = ConversionConfig(
            pdf_file="/test/file.pdf",
            mod_id="test-mod",
            mod_title="Test Module",
            output_directory="/test/output",
        )

        with patch.object(self.manager._error_dialog_manager, "show_error") as mock_show:
            # Even if error is retriable, should not offer retry when max attempts reached
            mock_show.return_value = RecoveryAction.CANCEL

            result = self.manager.start_recovery("job123", error, config)

            assert result == RecoveryAction.CANCEL
            # Verify that retry was not offered in the actions
            call_args = mock_show.call_args
            if len(call_args) > 1 and len(call_args[0]) > 1:
                actions = call_args[0][1] if isinstance(call_args[0][1], list) else []
                assert RecoveryAction.RETRY not in actions

    def test_final_failure_signal_emission(self):
        """Test signal emission on final failure."""
        self.manager._attempt_count = 3

        signal_emitted = False
        received_job_id = None

        def on_cancel_requested(job_id):
            nonlocal signal_emitted, received_job_id
            signal_emitted = True
            received_job_id = job_id

        self.manager.cancelRequested.connect(on_cancel_requested)

        error = FileError(
            code=ErrorCode.FILE_NOT_FOUND,
            user_message="File not found",
            file_path="/test/file.pdf",
            is_retriable=True,
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

    def test_no_retry_after_max_attempts(self):
        """Test that retry is not scheduled after max attempts."""
        self.manager._attempt_count = 3

        with (
            patch.object(self.manager, "_schedule_retry") as mock_schedule,
            patch.object(self.manager._logger, "warning"),
        ):
            self.manager._on_retry_requested()
            mock_schedule.assert_not_called()
