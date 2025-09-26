"""
Conversion handling functionality for the PDF2Foundry GUI.

This module contains the ConversionHandler class which manages
all conversion-related operations and UI updates.
"""

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QTimer, Slot
from PySide6.QtWidgets import QMessageBox

from core.gui_mapping import GuiMappingError
from core.threading import ConversionController
from gui.utils.styling import apply_status_style
from gui.widgets.status_indicator import StatusState

if TYPE_CHECKING:
    from gui.main_window import MainWindow


class ConversionHandler(QObject):
    """
    Handles all conversion-related operations and UI updates.

    This class manages the conversion workflow, including validation,
    starting/stopping conversions, and updating the UI based on
    conversion events.
    """

    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__(parent=main_window)
        self._main_window = main_window
        self._logger = logging.getLogger(__name__)

        # Create conversion controller
        self._conversion_controller = ConversionController(parent=self)

        # Progress throttling state
        self._progress_throttle_ms = 100  # 100ms throttle for smooth updates
        self._progress_timer = QTimer(self)
        self._progress_timer.setSingleShot(True)
        self._progress_timer.timeout.connect(self._apply_throttled_progress)
        self._last_progress_percent = 0
        self._last_progress_message = ""
        self._conversion_started = False

        # Connect controller signals with queued connections for thread safety
        self._conversion_controller.conversionStarted.connect(self._on_conversion_started)
        self._conversion_controller.conversionFinished.connect(self._on_conversion_finished)
        self._conversion_controller.progressChanged.connect(self.on_progress_changed)
        self._conversion_controller.logMessage.connect(self.on_log_message)
        self._conversion_controller.conversionCompleted.connect(self.on_conversion_completed)
        self._conversion_controller.conversionError.connect(self.on_conversion_error)
        self._conversion_controller.conversionCanceled.connect(self.on_conversion_canceled)

    @property
    def controller(self) -> ConversionController:
        """Get the conversion controller."""
        return self._conversion_controller

    def _set_status_state(self, state: StatusState) -> None:
        """Update the main window status indicator."""
        self._main_window._set_status(state)

    def validate_inputs(self) -> None:
        """Validate inputs and enable/disable convert button."""
        has_file = self._main_window.selected_file_path is not None
        has_mod_id = bool(self._main_window.module_id_input.text().strip())
        has_mod_title = bool(self._main_window.module_title_input.text().strip())
        is_not_converting = not self._conversion_controller.is_running()

        self._main_window.convert_button.setEnabled(has_file and has_mod_id and has_mod_title and is_not_converting)

    def start_conversion(self) -> None:
        """Handle convert button click."""
        if self._conversion_controller.is_running():
            return

        try:
            # Build GUI state
            gui_state = {
                "pdf_path": self._main_window.selected_file_path,
                "mod_id": self._main_window.module_id_input.text().strip(),
                "mod_title": self._main_window.module_title_input.text().strip(),
            }

            # Convert to ConversionConfig
            config = self._main_window._gui_mapper.build_config_from_gui(gui_state)

            # Start conversion
            self._conversion_controller.start_conversion(config)

        except GuiMappingError as e:
            self._show_error("Configuration Error", str(e))
        except Exception as e:
            self._show_error("Unexpected Error", f"Failed to start conversion: {e}")

    def cancel_conversion(self) -> None:
        """Handle cancel button click."""
        self._conversion_controller.cancel_conversion()
        self._main_window.log_console.append_log("INFO", "Cancellation requested...")

    @Slot()
    def _on_conversion_started(self) -> None:
        """Handle conversion started signal."""
        self._set_conversion_state(True)
        self._main_window.log_console.clear()
        self._main_window.log_console.append_log("INFO", "Starting conversion...")

        # Reset progress state
        self._conversion_started = False
        self._last_progress_percent = 0
        self._last_progress_message = ""
        self._progress_timer.stop()

        # Initialize progress bar
        self._main_window.progress_bar.setRange(0, 100)
        self._main_window.progress_bar.setValue(0)
        self._main_window.progress_bar.setFormat("%p%")

    @Slot()
    def _on_conversion_finished(self) -> None:
        """Handle conversion finished signal."""
        self._set_conversion_state(False)

    @Slot(int, str)
    def on_progress_changed(self, percent: int, message: str) -> None:
        """Handle progress updates from worker with throttling."""
        # Set status to Running on first progress update
        if not self._conversion_started:
            self._set_status_state(StatusState.RUNNING)
            self._conversion_started = True

        # Store latest progress values
        self._last_progress_percent = percent
        self._last_progress_message = message

        # Start/restart throttle timer
        self._progress_timer.stop()
        self._progress_timer.start(self._progress_throttle_ms)

    def _apply_throttled_progress(self) -> None:
        """Apply the latest throttled progress update to UI."""
        percent = self._last_progress_percent
        message = self._last_progress_message

        # Handle indeterminate progress for unknown phases
        if percent < 0 or any(keyword in message.lower() for keyword in ["preparing", "loading", "initializing"]):
            # Set indeterminate mode
            self._main_window.progress_bar.setRange(0, 0)
        else:
            # Set determinate mode with clamped value
            self._main_window.progress_bar.setRange(0, 100)
            clamped_percent = max(0, min(100, percent))
            self._main_window.progress_bar.setValue(clamped_percent)

            # Update format with message if provided
            if message:
                self._main_window.progress_bar.setFormat(f"{clamped_percent}% — {message}")
                self._main_window.progress_bar.setToolTip(message)
            else:
                self._main_window.progress_bar.setFormat("%p%")
                self._main_window.progress_bar.setToolTip("")

        # Update secondary status label
        if message:
            self._main_window.progress_status.setText(message)

    @Slot(str, str)
    def on_log_message(self, level: str, message: str) -> None:
        """Handle log messages from worker."""
        self._main_window.log_console.append_log(level, message)

    @Slot(dict)
    def on_conversion_completed(self, result: dict) -> None:
        """Handle successful conversion completion."""
        # Stop progress throttling and set final state
        self._progress_timer.stop()

        self._set_status_state(StatusState.COMPLETED)

        # Set progress to 100% completion
        self._main_window.progress_bar.setRange(0, 100)
        self._main_window.progress_bar.setValue(100)
        self._main_window.progress_bar.setFormat("100% — Completed")

        output_dir = result.get("output_dir", "")
        mod_title = result.get("mod_title", "Module")

        self._main_window.status_label.setText(f"Conversion completed: {mod_title}")
        apply_status_style(self._main_window.status_label, "success")

        self._main_window.log_console.append_log("INFO", "✓ Conversion completed successfully!")
        self._main_window.log_console.append_log("INFO", f"Output directory: {output_dir}")

    @Slot(str, str)
    def on_conversion_error(self, error_type: str, traceback_str: str) -> None:
        """Handle conversion errors."""
        # Stop progress throttling and set error state
        self._progress_timer.stop()

        self._set_status_state(StatusState.ERROR)

        # Keep current progress value (don't jump to 100%)
        self._main_window.progress_bar.setFormat(f"Error — {error_type}")

        self._main_window.status_label.setText(f"Conversion failed: {error_type}")
        apply_status_style(self._main_window.status_label, "error")

        self._main_window.log_console.append_log("ERROR", f"✗ Conversion failed: {error_type}")
        self._main_window.log_console.append_log("ERROR", f"Error details: {traceback_str}")

    @Slot()
    def on_conversion_canceled(self) -> None:
        """Handle conversion cancellation."""
        # Stop progress throttling and set canceled state
        self._progress_timer.stop()

        self._set_status_state(StatusState.IDLE)  # Return to idle after cancellation

        # Reset progress after brief delay to show cancellation
        QTimer.singleShot(1000, lambda: self._reset_progress_after_cancel())
        self._main_window.progress_bar.setFormat("Canceled")

        self._main_window.status_label.setText("Conversion canceled")
        apply_status_style(self._main_window.status_label, "warning")

        self._main_window.log_console.append_log("WARNING", "⚠ Conversion canceled by user")

    def _reset_progress_after_cancel(self) -> None:
        """Reset progress bar after cancellation delay."""
        self._main_window.progress_bar.setRange(0, 100)
        self._main_window.progress_bar.setValue(0)
        self._main_window.progress_bar.setFormat("%p%")

    def _set_conversion_state(self, is_converting: bool) -> None:
        """Update UI state based on conversion status."""
        # Update button states
        cancel_button = self._main_window.cancel_button
        if hasattr(cancel_button, "setEnabled"):
            cancel_button.setEnabled(is_converting)
        self.validate_inputs()  # This will update convert button state

        # Update progress visibility
        self._main_window.progress_bar.setVisible(is_converting)
        self._main_window.progress_status.setVisible(is_converting)

        if is_converting:
            self._main_window.progress_bar.setValue(0)
            self._main_window.progress_status.setText("Initializing...")
        else:
            # Reset to idle state when not converting (unless already in terminal state)
            if not self._conversion_started:  # Only reset if we haven't started yet
                self._set_status_state(StatusState.IDLE)

            self._main_window.progress_bar.setValue(0)
            self._main_window.progress_status.setText("")

    def _show_error(self, title: str, message: str) -> None:
        """Show an error message to the user."""
        msg_box = QMessageBox(self._main_window)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec()

    def cleanup(self) -> None:
        """Clean up resources when the handler is being destroyed."""
        self.shutdown()

    def shutdown(self, timeout_ms: int = 2000) -> None:
        """Handle application shutdown gracefully."""
        if self._conversion_controller.is_running():
            self._logger.info("Application closing with active conversion, requesting shutdown...")
            self._conversion_controller.shutdown(timeout_ms=timeout_ms)
