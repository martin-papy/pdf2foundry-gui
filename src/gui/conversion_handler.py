"""
Conversion handling for the PDF2Foundry GUI.

This module manages the conversion workflow, including validation,
starting/stopping conversions, and updating the UI based on conversion events.
"""

import logging
import uuid
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QMessageBox

from core.conversion_state import ConversionState
from core.gui_mapping import GuiConfigMapper, GuiMappingError
from core.threading import ConversionController
from gui.conversion.ui_manager import ConversionUIManager
from gui.conversion.validation import ConversionValidator
from gui.widgets.status_indicator import StatusState

if TYPE_CHECKING:
    from gui.main_window import MainWindow


class ConversionHandler(QObject):
    """
    Handles PDF conversion operations and UI updates.

    This class manages the conversion workflow, including validation,
    starting/stopping conversions, and updating the UI based on conversion events.
    """

    def __init__(self, main_window: "MainWindow") -> None:
        """Initialize the conversion handler."""
        super().__init__()
        self._main_window = main_window
        self._logger = logging.getLogger(__name__)

        # Initialize components
        self.validator = ConversionValidator(main_window)
        self.ui_manager = ConversionUIManager(main_window)

        # Conversion state tracking
        self._current_job_id: str | None = None
        self._conversion_id: str | None = None
        self._in_progress = False
        self._cancel_requested = False
        self._result_notified = False
        self._conversion_started = False

        # Progress throttling
        self._progress_throttle_timer = QTimer()
        self._progress_throttle_timer.setSingleShot(True)
        self._progress_throttle_timer.timeout.connect(self._apply_throttled_progress)
        self._pending_progress: tuple[int, str] | None = None

        # Initialize conversion controller
        self._conversion_controller = ConversionController()
        self._connect_controller_signals()

    def _connect_controller_signals(self) -> None:
        """Connect conversion controller signals."""
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
        """Set the status indicator state."""
        self._main_window.ui_state_handler._set_status(state)

    def validate_inputs(self) -> None:
        """Validate conversion inputs and update UI accordingly."""
        # This method can be expanded if needed
        pass

    def start_conversion(self) -> None:
        """Start the PDF conversion process."""
        # Generate unique conversion ID for this attempt
        self._conversion_id = str(uuid.uuid4())[:8]
        self._result_notified = False

        try:
            # Perform pre-flight checks
            checks_passed, error_message = self.validator._perform_preflight_checks()
            if not checks_passed:
                self._show_error("Cannot Start Conversion", error_message)
                return

            # Set conversion flags
            self._in_progress = True
            self._cancel_requested = False

            # Update UI state
            self._main_window.set_conversion_state(ConversionState.RUNNING)

            # Build conversion configuration
            gui_mapper = GuiConfigMapper()

            # Create GUI state dictionary
            gui_state = {
                "pdf_file": self._main_window.file_handler.get_selected_pdf_path() or "",
                "mod_id": (self._main_window.ui.module_id_input.text() if self._main_window.ui.module_id_input else ""),
                "mod_title": (
                    self._main_window.ui.module_title_input.text() if self._main_window.ui.module_title_input else ""
                ),
                "output_dir": (
                    self._main_window.ui.output_dir_selector.path() if self._main_window.ui.output_dir_selector else ""
                ),
            }

            config = gui_mapper.build_config_from_gui(gui_state)

            # Generate job ID
            self._current_job_id = f"{config.mod_id}-{self._conversion_id}"

            # Start the conversion
            self._conversion_controller.start_conversion(config)

        except GuiMappingError as e:
            self.ui_manager._finalize_conversion("error", {"error_type": "Configuration Error", "message": str(e)})
        except Exception as e:
            self._logger.error(f"[{self._conversion_id}] Unexpected error starting conversion: {e}")
            self.ui_manager._finalize_conversion("error", {"error_type": "Startup Error", "message": str(e)})

    def cancel_conversion(self) -> None:
        """Cancel the current conversion."""
        self._cancel_requested = True

        # Disable cancel button to prevent multiple clicks
        if self._main_window.ui.cancel_button:
            self._main_window.ui.cancel_button.setEnabled(False)

        # If conversion hasn't started yet, finalize immediately
        if not self._conversion_controller.is_running():
            self.ui_manager._finalize_conversion("cancelled")
            return

        # Request cancellation from controller
        self._conversion_controller.cancel_conversion()

    def _on_conversion_started(self) -> None:
        """Handle conversion started signal."""
        self._conversion_started = True
        self._set_status_state(StatusState.RUNNING)

        # Clear and initialize log console
        if hasattr(self._main_window, "log_console") and self._main_window.log_console:
            self._main_window.log_console.clear()
            self._main_window.log_console.append_log("INFO", "Starting conversion...")

        # Update progress bar
        if hasattr(self._main_window, "progress_bar"):
            self._main_window.progress_bar.setVisible(True)
            self._main_window.progress_bar.setValue(0)
            self._main_window.progress_bar.setFormat("%p%")  # Reset to default format

        if hasattr(self._main_window, "progress_status"):
            self._main_window.progress_status.setVisible(True)
            self._main_window.progress_status.setText("Initializing...")

    def _on_conversion_finished(self) -> None:
        """Handle conversion finished signal."""
        # This is called for all completion types (success, error, cancel)
        # The specific handlers will be called separately
        pass

    def on_progress_changed(self, percent: int, message: str) -> None:
        """
        Handle progress update from conversion.

        Args:
            percent: Progress percentage (0-100)
            message: Progress message
        """
        # If this is the first progress update, set status to RUNNING
        if not self._conversion_started:
            self._conversion_started = True
            self._set_status_state(StatusState.RUNNING)

        # Clamp percentage to valid range
        percent = max(0, min(100, percent))

        # Store pending progress for throttling
        self._pending_progress = (percent, message)

        # Start or restart throttle timer (16ms = ~60fps)
        if not self._progress_throttle_timer.isActive():
            self._progress_throttle_timer.start(16)

    def _apply_throttled_progress(self) -> None:
        """Apply the most recent progress update."""
        if not self._pending_progress:
            return

        percent, message = self._pending_progress
        self._pending_progress = None

        # Handle negative values or indeterminate keywords (indeterminate mode)
        indeterminate_keywords = ["preparing", "loading", "initializing"]
        is_indeterminate = percent < 0 or any(keyword in message.lower() for keyword in indeterminate_keywords)

        if is_indeterminate:
            if hasattr(self._main_window, "progress_bar"):
                self._main_window.progress_bar.setMinimum(0)
                self._main_window.progress_bar.setMaximum(0)
                self._main_window.progress_bar.setValue(0)
                if message:
                    self._main_window.progress_bar.setFormat(message)
        else:
            # Clamp percentage to valid range
            percent = max(0, min(100, percent))

            # Update progress bar
            if hasattr(self._main_window, "progress_bar"):
                # Reset to normal mode if it was in indeterminate mode
                if self._main_window.progress_bar.maximum() == 0:
                    self._main_window.progress_bar.setMinimum(0)
                    self._main_window.progress_bar.setMaximum(100)

                self._main_window.progress_bar.setValue(percent)
                if message:
                    self._main_window.progress_bar.setFormat(f"{percent}% — {message}")
                    self._main_window.progress_bar.setToolTip(message)

        # Update status label
        if hasattr(self._main_window, "progress_status"):
            self._main_window.progress_status.setText(message or f"{percent}%")

    def on_log_message(self, level: str, message: str) -> None:
        """Handle log message from conversion."""
        if hasattr(self._main_window, "log_console"):
            self._main_window.log_console.append_log(level, message)

    def on_conversion_completed(self, result: dict) -> None:
        """Handle successful conversion completion."""
        self._logger.info(f"[{self._conversion_id or 'unknown'}] Conversion completed successfully")

        # Update progress to 100%
        if hasattr(self._main_window, "progress_bar"):
            self._main_window.progress_bar.setValue(100)
            self._main_window.progress_bar.setFormat("100% — Completed")

        if hasattr(self._main_window, "progress_status"):
            self._main_window.progress_status.setText("Conversion completed successfully")

        # Set status to completed
        self._set_status_state(StatusState.COMPLETED)

        # Send notification
        if hasattr(self._main_window, "notification_manager") and not self._result_notified:
            output_path = result.get("output_path")
            pages = result.get("pages_processed", "unknown")
            module_title = result.get("module_title", "PDF")

            self._main_window.notification_manager.notify(
                status="success",
                title="Conversion Completed",
                message=f"Successfully converted {pages} pages of '{module_title}'",
                output_path=output_path,
                job_id=self._current_job_id,
            )

        # Finalize conversion
        self.ui_manager._finalize_conversion("success", result)

    def on_conversion_error(self, error_type: str, traceback_str: str) -> None:
        """Handle conversion error."""
        self._logger.error(f"[{self._conversion_id or 'unknown'}] Conversion failed: {error_type}")

        # Update progress bar with error
        if hasattr(self._main_window, "progress_bar"):
            self._main_window.progress_bar.setFormat(f"Error — {error_type}")

        if hasattr(self._main_window, "progress_status"):
            self._main_window.progress_status.setText(f"Error: {error_type}")

        # Set status to error
        self._set_status_state(StatusState.ERROR)

        # Send notification
        if hasattr(self._main_window, "notification_manager") and not self._result_notified:
            self._main_window.notification_manager.notify(
                status="error", title="Conversion Failed", message=f"Error: {error_type}", job_id=self._current_job_id
            )

        # Finalize conversion
        self.ui_manager._finalize_conversion("error", {"error_type": error_type, "traceback": traceback_str})

    def on_conversion_canceled(self) -> None:
        """Handle conversion cancellation."""
        self._logger.info(f"[{self._conversion_id or 'unknown'}] Conversion cancelled by user")

        # Set progress bar format to "Canceled" immediately
        if hasattr(self._main_window, "progress_bar"):
            self._main_window.progress_bar.setFormat("Canceled")

        # Schedule progress reset after a delay
        from PySide6.QtCore import QTimer

        QTimer.singleShot(1000, self._reset_progress_after_cancel)

        if hasattr(self._main_window, "progress_status"):
            self._main_window.progress_status.setText("Conversion canceled")

        # Set status to idle
        self._set_status_state(StatusState.IDLE)

        # Send notification
        if hasattr(self._main_window, "notification_manager") and not self._result_notified:
            self._main_window.notification_manager.notify(
                status="warning",
                title="Conversion Canceled",
                message="The conversion was canceled by the user",
                job_id=self._current_job_id,
            )

        # Finalize conversion
        self.ui_manager._finalize_conversion("cancelled")

    def _show_error(self, title: str, message: str) -> None:
        """Show an error message to the user."""
        QMessageBox.critical(self._main_window, title, message)
        self._logger.error(f"{title}: {message}")

    def _reset_progress_after_cancel(self) -> None:
        """Reset progress bar after cancellation delay."""
        if hasattr(self._main_window, "progress_bar"):
            self._main_window.progress_bar.setValue(0)
            self._main_window.progress_bar.setFormat("%p%")

    def cleanup(self) -> None:
        """Clean up resources."""
        self._conversion_controller.shutdown()

    def shutdown(self, timeout_ms: int = 2000) -> None:
        """Shutdown the conversion handler."""
        self._conversion_controller.shutdown(timeout_ms)
