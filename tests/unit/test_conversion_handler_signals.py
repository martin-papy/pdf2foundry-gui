"""
Tests for ConversionHandler signal connections and status management.

This module tests the signal connections between the ConversionController
and the UI components, ensuring proper status state transitions, progress
updates, and log routing.
"""

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow
from gui.widgets.status_indicator import StatusState


@pytest.fixture
def app():
    """Create QApplication instance for testing."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def main_window(app):
    """Create MainWindow instance for testing."""
    return MainWindow()


@pytest.fixture
def conversion_handler(main_window):
    """Create ConversionHandler instance for testing."""
    return main_window.conversion_handler


class TestConversionHandlerSignals:
    """Test signal connections and status management."""

    def test_initial_status_state(self, conversion_handler, main_window):
        """Test that initial status is set to IDLE."""
        # The status should be set to IDLE during MainWindow initialization
        assert main_window.status_text.text() == StatusState.IDLE.display_name

    def test_conversion_started_signal(self, conversion_handler, main_window):
        """Test conversion started signal handling."""
        # Mock the log console to avoid actual UI updates
        main_window.log_console.clear = MagicMock()
        main_window.log_console.append_log = MagicMock()

        # Trigger conversion started
        conversion_handler._on_conversion_started()

        # Verify log console was cleared and initialized
        main_window.log_console.clear.assert_called_once()
        main_window.log_console.append_log.assert_called_with("INFO", "Starting conversion...")

        # Verify progress bar initialization
        assert main_window.progress_bar.minimum() == 0
        assert main_window.progress_bar.maximum() == 100
        assert main_window.progress_bar.value() == 0
        assert main_window.progress_bar.format() == "%p%"

    def test_progress_changed_sets_running_status(self, conversion_handler, main_window):
        """Test that first progress update sets status to RUNNING."""
        # Reset conversion started flag
        conversion_handler._conversion_started = False

        # Trigger progress update
        conversion_handler.on_progress_changed(25, "Processing pages...")

        # Process any pending timer events
        QTimer.singleShot(0, lambda: None)
        QApplication.processEvents()

        # Verify status was set to RUNNING
        assert main_window.status_text.text() == StatusState.RUNNING.display_name
        assert conversion_handler._conversion_started is True

    def test_progress_throttling(self, conversion_handler, main_window):
        """Test that progress updates are throttled."""
        conversion_handler._conversion_started = True  # Skip status change

        # Send multiple rapid progress updates
        conversion_handler.on_progress_changed(10, "Step 1")
        conversion_handler.on_progress_changed(20, "Step 2")
        conversion_handler.on_progress_changed(30, "Step 3")

        # Verify timer is running (throttling active)
        assert conversion_handler._progress_timer.isActive()

        # Verify latest values are stored
        assert conversion_handler._last_progress_percent == 30
        assert conversion_handler._last_progress_message == "Step 3"

    def test_progress_clamping(self, conversion_handler, main_window):
        """Test that progress values are clamped to 0-100 range."""
        conversion_handler._conversion_started = True

        # Test values outside valid range
        conversion_handler._last_progress_percent = 150
        conversion_handler._last_progress_message = "Over 100%"
        conversion_handler._apply_throttled_progress()

        assert main_window.progress_bar.value() == 100

        conversion_handler._last_progress_percent = -10
        conversion_handler._last_progress_message = "Negative"
        conversion_handler._apply_throttled_progress()

        # Negative values should trigger indeterminate mode
        assert main_window.progress_bar.minimum() == 0
        assert main_window.progress_bar.maximum() == 0

    def test_indeterminate_progress_mode(self, conversion_handler, main_window):
        """Test indeterminate progress mode for unknown phases."""
        conversion_handler._conversion_started = True

        # Test keywords that trigger indeterminate mode
        test_cases = [
            (-1, "Unknown progress"),
            (50, "Preparing files..."),
            (25, "Loading modules..."),
            (75, "Initializing conversion..."),
        ]

        for percent, message in test_cases:
            conversion_handler._last_progress_percent = percent
            conversion_handler._last_progress_message = message
            conversion_handler._apply_throttled_progress()

            # Should be in indeterminate mode (range 0-0)
            assert main_window.progress_bar.minimum() == 0
            assert main_window.progress_bar.maximum() == 0

    def test_log_message_routing(self, conversion_handler, main_window):
        """Test that log messages are routed to LogConsole."""
        main_window.log_console.append_log = MagicMock()

        # Test different log levels
        conversion_handler.on_log_message("INFO", "Information message")
        conversion_handler.on_log_message("WARNING", "Warning message")
        conversion_handler.on_log_message("ERROR", "Error message")

        # Verify all messages were routed
        expected_calls = [
            (("INFO", "Information message"),),
            (("WARNING", "Warning message"),),
            (("ERROR", "Error message"),),
        ]

        assert main_window.log_console.append_log.call_count == 3
        for i, expected_call in enumerate(expected_calls):
            actual_call = main_window.log_console.append_log.call_args_list[i]
            assert actual_call.args == expected_call[0]

    def test_conversion_completed_status(self, conversion_handler, main_window):
        """Test conversion completed signal handling."""
        conversion_handler._conversion_started = True
        main_window.log_console.append_log = MagicMock()

        result = {
            "output_dir": "/path/to/output",
            "mod_title": "Test Module",
        }

        conversion_handler.on_conversion_completed(result)

        # Verify status set to COMPLETED
        assert main_window.status_text.text() == StatusState.COMPLETED.display_name

        # Verify progress set to 100%
        assert main_window.progress_bar.value() == 100
        assert main_window.progress_bar.format() == "100% — Completed"

        # Verify timer stopped
        assert not conversion_handler._progress_timer.isActive()

    def test_conversion_error_status(self, conversion_handler, main_window):
        """Test conversion error signal handling."""
        conversion_handler._conversion_started = True
        main_window.log_console.append_log = MagicMock()

        # Set some progress first
        main_window.progress_bar.setValue(50)

        conversion_handler.on_conversion_error("TestError", "Test traceback")

        # Verify status set to ERROR
        assert main_window.status_text.text() == StatusState.ERROR.display_name

        # Verify progress value preserved (not jumped to 100%)
        assert main_window.progress_bar.value() == 50
        assert "Error — TestError" in main_window.progress_bar.format()

        # Verify timer stopped
        assert not conversion_handler._progress_timer.isActive()

    def test_conversion_canceled_status(self, conversion_handler, main_window):
        """Test conversion canceled signal handling."""
        conversion_handler._conversion_started = True
        main_window.log_console.append_log = MagicMock()

        conversion_handler.on_conversion_canceled()

        # Verify status set to IDLE (after cancellation)
        assert main_window.status_text.text() == StatusState.IDLE.display_name

        # Verify progress format shows canceled
        assert main_window.progress_bar.format() == "Canceled"

        # Verify timer stopped
        assert not conversion_handler._progress_timer.isActive()

    def test_progress_format_with_message(self, conversion_handler, main_window):
        """Test progress bar format includes message when provided."""
        conversion_handler._conversion_started = True

        conversion_handler._last_progress_percent = 75
        conversion_handler._last_progress_message = "Processing images..."
        conversion_handler._apply_throttled_progress()

        assert main_window.progress_bar.format() == "75% — Processing images..."
        assert main_window.progress_bar.toolTip() == "Processing images..."

    def test_progress_format_without_message(self, conversion_handler, main_window):
        """Test progress bar format when no message provided."""
        conversion_handler._conversion_started = True

        conversion_handler._last_progress_percent = 50
        conversion_handler._last_progress_message = ""
        conversion_handler._apply_throttled_progress()

        assert main_window.progress_bar.format() == "%p%"
        assert main_window.progress_bar.toolTip() == ""

    def test_status_state_helper_method(self, conversion_handler, main_window):
        """Test the status state helper method."""
        # Test all status states
        for state in StatusState:
            conversion_handler._set_status_state(state)
            assert main_window.status_text.text() == state.display_name

            # Verify dot color matches state color
            style = main_window.status_dot.styleSheet()
            assert state.color in style

    @patch("PySide6.QtCore.QTimer.singleShot")
    def test_reset_progress_after_cancel_delay(self, mock_single_shot, conversion_handler, main_window):
        """Test that progress reset is scheduled after cancellation."""
        conversion_handler.on_conversion_canceled()

        # Verify QTimer.singleShot was called with 1000ms delay
        mock_single_shot.assert_called_once()
        args = mock_single_shot.call_args[0]
        assert args[0] == 1000  # 1 second delay

        # Call the scheduled function manually
        reset_function = args[1]
        reset_function()

        # Verify progress was reset
        assert main_window.progress_bar.value() == 0
        assert main_window.progress_bar.format() == "%p%"
