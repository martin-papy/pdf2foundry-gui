"""
Conversion handling functionality for the PDF2Foundry GUI.

This module contains the ConversionHandler class which manages
all conversion-related operations and UI updates.
"""

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Slot
from PySide6.QtWidgets import QMessageBox

from core.gui_mapping import GuiMappingError
from core.threading import ConversionController

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

        # Connect controller signals
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
        self._main_window.log_text.append("Cancellation requested...")

    @Slot()
    def _on_conversion_started(self) -> None:
        """Handle conversion started signal."""
        self._set_conversion_state(True)
        self._main_window.log_text.clear()
        self._main_window.log_text.append("Starting conversion...")

    @Slot()
    def _on_conversion_finished(self) -> None:
        """Handle conversion finished signal."""
        self._set_conversion_state(False)

    @Slot(int, str)
    def on_progress_changed(self, percent: int, message: str) -> None:
        """Handle progress updates from worker."""
        self._main_window.progress_bar.setValue(percent)
        if message:
            self._main_window.progress_status.setText(message)

    @Slot(str, str)
    def on_log_message(self, level: str, message: str) -> None:
        """Handle log messages from worker."""
        formatted_message = f"[{level}] {message}"
        self._main_window.log_text.append(formatted_message)
        # Auto-scroll to bottom
        scrollbar = self._main_window.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    @Slot(dict)
    def on_conversion_completed(self, result: dict) -> None:
        """Handle successful conversion completion."""
        output_dir = result.get("output_dir", "")
        mod_title = result.get("mod_title", "Module")

        self._main_window.status_label.setText(f"Conversion completed: {mod_title}")
        self._main_window.status_label.setStyleSheet(
            """
            QLabel {
                color: #155724;
                font-size: 14px;
                font-weight: bold;
                padding: 8px;
                background-color: #d4edda;
                border: 1px solid #c3e6cb;
                border-radius: 4px;
            }
        """
        )

        self._main_window.log_text.append("\n✓ Conversion completed successfully!")
        self._main_window.log_text.append(f"Output directory: {output_dir}")

    @Slot(str, str)
    def on_conversion_error(self, error_type: str, traceback_str: str) -> None:
        """Handle conversion errors."""
        self._main_window.status_label.setText(f"Conversion failed: {error_type}")
        self._main_window.status_label.setStyleSheet(
            """
            QLabel {
                color: #721c24;
                font-size: 14px;
                font-weight: bold;
                padding: 8px;
                background-color: #f8d7da;
                border: 1px solid #f5c6cb;
                border-radius: 4px;
            }
        """
        )

        self._main_window.log_text.append(f"\n✗ Conversion failed: {error_type}")
        self._main_window.log_text.append(f"Error details: {traceback_str}")

    @Slot()
    def on_conversion_canceled(self) -> None:
        """Handle conversion cancellation."""
        self._main_window.status_label.setText("Conversion canceled")
        self._main_window.status_label.setStyleSheet(
            """
            QLabel {
                color: #856404;
                font-size: 14px;
                font-weight: bold;
                padding: 8px;
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 4px;
            }
        """
        )

        self._main_window.log_text.append("\n⚠ Conversion canceled by user")

    def _set_conversion_state(self, is_converting: bool) -> None:
        """Update UI state based on conversion status."""
        # Update button states
        self._main_window.cancel_button.setEnabled(is_converting)
        self.validate_inputs()  # This will update convert button state

        # Update progress visibility
        self._main_window.progress_bar.setVisible(is_converting)
        self._main_window.progress_status.setVisible(is_converting)

        if is_converting:
            self._main_window.progress_bar.setValue(0)
            self._main_window.progress_status.setText("Initializing...")
        else:
            self._main_window.progress_bar.setValue(0)
            self._main_window.progress_status.setText("")

    def _show_error(self, title: str, message: str) -> None:
        """Show an error message to the user."""
        msg_box = QMessageBox(self._main_window)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec()

    def shutdown(self, timeout_ms: int = 2000) -> None:
        """Handle application shutdown gracefully."""
        if self._conversion_controller.is_running():
            self._logger.info("Application closing with active conversion, requesting shutdown...")
            self._conversion_controller.shutdown(timeout_ms=timeout_ms)
