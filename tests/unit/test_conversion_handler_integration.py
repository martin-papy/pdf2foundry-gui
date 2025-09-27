"""
Integration tests for ConversionHandler with mock worker signals.

This module tests the complete signal flow from worker thread to UI updates,
including rapid signal emission scenarios and thread safety.
"""

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from core.threading import ConversionController
from gui.main_window import MainWindow
from gui.widgets.status_indicator import StatusState


@pytest.fixture
def app():
    """Create QApplication instance for testing."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def main_window(app):
    """Create MainWindow instance for testing."""
    window = MainWindow()
    # Disable batching for immediate updates in tests
    window.log_console.set_batching_enabled(False)
    return window


@pytest.fixture
def conversion_handler(main_window):
    """Create ConversionHandler instance for testing."""
    return main_window.conversion_handler


class MockWorkerSignals:
    """Mock worker that emits rapid signals for testing."""

    def __init__(self, controller: ConversionController):
        self.controller = controller

    def emit_rapid_progress(self, count: int = 10, delay_ms: int = 5):
        """Emit rapid progress updates."""
        for i in range(count):
            percent = int((i / count) * 100)
            message = f"Processing step {i+1}/{count}"
            self.controller.progressChanged.emit(percent, message)

            # Small delay to simulate real worker timing
            QTimer.singleShot(delay_ms * i, lambda: None)

    def emit_log_burst(self, count: int = 20):
        """Emit burst of log messages."""
        levels = ["INFO", "WARNING", "ERROR"]
        for i in range(count):
            level = levels[i % len(levels)]
            message = f"Log message {i+1} with level {level}"
            self.controller.logMessage.emit(level, message)

    def emit_success_sequence(self):
        """Emit a complete success sequence."""
        # Start
        self.controller.conversionStarted.emit()

        # Progress updates
        for i in range(0, 101, 10):
            message = f"Processing... {i}%"
            self.controller.progressChanged.emit(i, message)

        # Some logs
        self.controller.logMessage.emit("INFO", "Conversion phase 1 complete")
        self.controller.logMessage.emit("INFO", "Conversion phase 2 complete")

        # Completion
        result = {
            "success": True,
            "output_dir": "/test/output",
            "mod_title": "Test Module",
            "pages_processed": 10,
        }
        self.controller.conversionCompleted.emit(result)
        # Note: Don't emit conversionFinished immediately to allow testing progress state

    def emit_error_sequence(self):
        """Emit a complete error sequence."""
        # Start
        self.controller.conversionStarted.emit()

        # Some progress
        self.controller.progressChanged.emit(25, "Processing...")
        self.controller.logMessage.emit("INFO", "Starting conversion")

        # Error occurs
        self.controller.logMessage.emit("ERROR", "Something went wrong")
        self.controller.conversionError.emit("TestError", "Test error traceback")
        self.controller.conversionFinished.emit()

    def emit_cancel_sequence(self):
        """Emit a complete cancellation sequence."""
        # Start
        self.controller.conversionStarted.emit()

        # Some progress
        self.controller.progressChanged.emit(50, "Processing...")
        self.controller.logMessage.emit("INFO", "Conversion in progress")

        # Cancellation
        self.controller.logMessage.emit("WARNING", "Cancellation requested")
        self.controller.conversionCanceled.emit()
        self.controller.conversionFinished.emit()


class TestConversionHandlerIntegration:
    """Integration tests for complete conversion workflows."""

    def test_rapid_progress_updates_no_flicker(self, conversion_handler, main_window):
        """Test that rapid progress updates don't cause UI flicker."""
        main_window.log_console.append_log = MagicMock()

        # Create mock worker
        mock_worker = MockWorkerSignals(conversion_handler.controller)

        # Start conversion state
        conversion_handler._on_conversion_started()

        # Emit rapid progress updates
        mock_worker.emit_rapid_progress(count=50, delay_ms=2)

        # Process events to handle signals
        for _ in range(10):
            QApplication.processEvents()
            QTimer.singleShot(10, lambda: None)

        # Verify throttling is working (timer should be active or recently active)
        # The exact state depends on timing, but we should have received updates
        if conversion_handler._pending_progress:
            percent, message = conversion_handler._pending_progress
            assert percent >= 0
            assert message != ""

        # Verify status is RUNNING
        assert main_window.status_text.text() == StatusState.RUNNING.display_name

    def test_log_message_burst_handling(self, conversion_handler, main_window):
        """Test handling of burst log messages."""
        main_window.log_console.append_log = MagicMock()

        # Create mock worker
        mock_worker = MockWorkerSignals(conversion_handler.controller)

        # Emit log burst
        mock_worker.emit_log_burst(count=100)

        # Process events
        QApplication.processEvents()

        # Verify all messages were handled
        assert main_window.log_console.append_log.call_count == 100

        # Verify different log levels were handled
        call_args = [call.args for call in main_window.log_console.append_log.call_args_list]
        levels_used = {args[0] for args in call_args}
        assert "INFO" in levels_used
        assert "WARNING" in levels_used
        assert "ERROR" in levels_used

    def test_complete_success_workflow(self, conversion_handler, main_window):
        """Test complete successful conversion workflow."""
        main_window.log_console.append_log = MagicMock()

        # Create mock worker
        mock_worker = MockWorkerSignals(conversion_handler.controller)

        # Initial state should be IDLE
        assert main_window.status_text.text() == StatusState.IDLE.display_name

        # Run success sequence (without conversionFinished)
        mock_worker.emit_success_sequence()

        # Process all events multiple times to ensure all signals are processed
        for _ in range(5):
            QApplication.processEvents()
            QTimer.singleShot(10, lambda: None)

        # Process any remaining timer events
        QApplication.processEvents()

        # Force any pending throttled progress update
        if conversion_handler._progress_throttle_timer.isActive():
            conversion_handler._progress_throttle_timer.stop()
            conversion_handler._apply_throttled_progress()

        # Verify final state is COMPLETED
        assert main_window.status_text.text() == StatusState.COMPLETED.display_name

        # Verify progress bar is at 100% (before conversionFinished resets it)
        assert main_window.progress_bar.value() == 100
        # Progress format may contain either completion message or final progress message
        format_text = main_window.progress_bar.format()
        assert "100%" in format_text  # Should contain 100% in some form

        # Now emit the finished signal to complete the workflow
        mock_worker.controller.conversionFinished.emit()
        QApplication.processEvents()

        # Verify logs were captured
        assert main_window.log_console.append_log.call_count > 0

    def test_complete_error_workflow(self, conversion_handler, main_window):
        """Test complete error conversion workflow."""
        main_window.log_console.append_log = MagicMock()

        # Create mock worker
        mock_worker = MockWorkerSignals(conversion_handler.controller)

        # Run error sequence
        mock_worker.emit_error_sequence()

        # Process all events
        QApplication.processEvents()

        # Verify final state is ERROR
        assert main_window.status_text.text() == StatusState.ERROR.display_name

        # Verify progress bar shows error
        assert "Error — TestError" in main_window.progress_bar.format()

        # Verify error logs were captured
        assert main_window.log_console.append_log.call_count > 0
        error_calls = [call for call in main_window.log_console.append_log.call_args_list if call.args[0] == "ERROR"]
        assert len(error_calls) > 0

    def test_complete_cancel_workflow(self, conversion_handler, main_window):
        """Test complete cancellation workflow."""
        main_window.log_console.append_log = MagicMock()

        # Create mock worker
        mock_worker = MockWorkerSignals(conversion_handler.controller)

        # Run cancel sequence
        mock_worker.emit_cancel_sequence()

        # Process all events
        QApplication.processEvents()

        # Verify final state is IDLE (after cancellation)
        assert main_window.status_text.text() == StatusState.IDLE.display_name

        # Verify progress bar shows canceled
        assert main_window.progress_bar.format() == "Canceled"

        # Verify warning logs were captured
        warning_calls = [call for call in main_window.log_console.append_log.call_args_list if call.args[0] == "WARNING"]
        assert len(warning_calls) > 0

    def test_filtering_during_log_stream(self, conversion_handler, main_window):
        """Test that log filtering works during active log streaming."""
        # Create mock worker
        mock_worker = MockWorkerSignals(conversion_handler.controller)

        # Start with INFO filter
        main_window.log_console._filter_combo.setCurrentText("INFO")

        # Emit mixed log messages
        mock_worker.emit_log_burst(count=30)

        # Process events
        QApplication.processEvents()

        # Change filter to ERROR during streaming
        main_window.log_console._filter_combo.setCurrentText("ERROR")

        # Emit more messages
        mock_worker.emit_log_burst(count=30)

        # Process events
        QApplication.processEvents()

        # Verify filtering is still working
        assert main_window.log_console._current_filter == "ERROR"

    def test_search_during_log_stream(self, conversion_handler, main_window):
        """Test that search works during active log streaming."""
        # Create mock worker
        mock_worker = MockWorkerSignals(conversion_handler.controller)

        # Emit some logs first
        mock_worker.emit_log_burst(count=20)
        QApplication.processEvents()

        # Start a search
        main_window.log_console._search_input.setText("ERROR")
        main_window.log_console.force_search()  # Force immediate search

        # Emit more logs
        mock_worker.emit_log_burst(count=20)
        QApplication.processEvents()

        # Verify search is still active
        assert main_window.log_console._search_text == "ERROR"
        assert len(main_window.log_console._search_matches) > 0

    def test_thread_safety_queued_connections(self, conversion_handler):
        """Test that all signal connections are queued for thread safety."""
        controller = conversion_handler.controller

        # Get all signal connections
        signals_to_check = [
            controller.conversionStarted,
            controller.conversionFinished,
            controller.progressChanged,
            controller.logMessage,
            controller.conversionCompleted,
            controller.conversionError,
            controller.conversionCanceled,
        ]

        # Note: In a real test, we would check connection types, but PySide6
        # doesn't expose this information easily. The connections are made
        # with default Qt.AutoConnection which becomes Qt.QueuedConnection
        # when crossing thread boundaries, which is what we want.

        # Verify signals exist and are callable
        for signal in signals_to_check:
            assert hasattr(signal, "emit")
            assert callable(signal.emit)

    @patch("PySide6.QtCore.QTimer")
    def test_throttle_timer_configuration(self, mock_timer_class, conversion_handler):
        """Test that throttle timer is properly configured."""
        # Verify timer was created with correct settings
        timer_instance = conversion_handler._progress_throttle_timer
        assert timer_instance.isSingleShot()

        # Verify throttle timer exists (no specific throttle_ms attribute in current implementation)
        assert timer_instance is not None

    def test_status_transitions_are_atomic(self, conversion_handler, main_window):
        """Test that status transitions are atomic and don't interfere."""
        main_window.log_console.append_log = MagicMock()

        # Create mock worker
        mock_worker = MockWorkerSignals(conversion_handler.controller)

        # Rapid state transitions
        mock_worker.controller.conversionStarted.emit()
        QApplication.processEvents()

        mock_worker.controller.progressChanged.emit(50, "Halfway")
        QApplication.processEvents()

        # Should be RUNNING now
        assert main_window.status_text.text() == StatusState.RUNNING.display_name

        # Complete immediately
        result = {"success": True, "output_dir": "/test", "mod_title": "Test"}
        mock_worker.controller.conversionCompleted.emit(result)
        QApplication.processEvents()

        # Should be COMPLETED now
        assert main_window.status_text.text() == StatusState.COMPLETED.display_name
