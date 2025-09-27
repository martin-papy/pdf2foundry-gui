"""
UI state management functionality for the main window.

This module contains methods for managing UI state, validation,
and conversion state transitions.
"""

import logging
from typing import TYPE_CHECKING

from core.conversion_state import ConversionState
from gui.widgets.status_indicator import StatusState

if TYPE_CHECKING:
    from gui.main_window import MainWindow


class UIStateHandler:
    """Handles UI state management for the main window."""

    def __init__(self, main_window: "MainWindow") -> None:
        """Initialize the UI state handler."""
        self.main_window = main_window
        self._logger = logging.getLogger(__name__)

    def _on_validation_changed(self) -> None:
        """Handle validation state changes."""
        # Check if we have a valid PDF file
        pdf_valid = bool(self.main_window.file_handler.get_selected_pdf_path())

        # Check if we have valid module inputs
        module_id_valid = bool(self.main_window.ui.module_id_input and self.main_window.ui.module_id_input.text().strip())
        module_title_valid = bool(
            self.main_window.ui.module_title_input and self.main_window.ui.module_title_input.text().strip()
        )

        # Check if output directory is valid
        output_valid = bool(self.main_window.ui.output_dir_selector and self.main_window.ui.output_dir_selector.is_valid())

        # Overall validation state
        self.main_window._validation_ok = pdf_valid and module_id_valid and module_title_valid and output_valid

        # Update UI state
        self.set_conversion_ui_state(self.main_window._current_conversion_state, self.main_window._validation_ok)

    def set_conversion_state(self, state: ConversionState) -> None:
        """
        Set the conversion state and update UI accordingly.

        Args:
            state: The new conversion state
        """
        self.main_window._current_conversion_state = state

        # Update status indicator
        if hasattr(self.main_window, "status_manager") and self.main_window.status_manager:
            self.main_window.status_manager.set_conversion_state(state)

        # Update UI state
        self.set_conversion_ui_state(state, self.main_window._validation_ok)

    def _update_convert_button_state(self) -> None:
        """Update the convert button enabled state based on validation."""
        self._on_validation_changed()

    def set_conversion_ui_state(self, state: ConversionState, validation_ok: bool = True) -> None:
        """
        Update UI elements based on conversion state and validation.

        Args:
            state: Current conversion state
            validation_ok: Whether validation passes
        """
        # Ensure we have the required UI elements
        if not (
            self.main_window.ui.convert_button
            and self.main_window.ui.cancel_button
            and self.main_window.ui.open_output_button
        ):
            return

        # Convert button state
        convert_enabled = state != ConversionState.RUNNING and validation_ok
        self.main_window.ui.convert_button.setEnabled(convert_enabled)

        # Set convert button as default when not running
        if state != ConversionState.RUNNING:
            self.main_window.ui.convert_button.setDefault(True)
            self.main_window.ui.convert_button.setAutoDefault(True)
        else:
            self.main_window.ui.convert_button.setDefault(False)
            self.main_window.ui.convert_button.setAutoDefault(False)

        # Cancel button state - only visible when running
        if state == ConversionState.RUNNING:
            self.main_window.ui.cancel_button.setVisible(True)
            self.main_window.ui.cancel_button.setEnabled(True)
        else:
            self.main_window.ui.cancel_button.setVisible(False)

        # Open output button state
        output_dir_valid = self.main_window.ui.output_dir_selector and self.main_window.ui.output_dir_selector.is_valid()
        open_output_enabled = bool(output_dir_valid) and state != ConversionState.RUNNING
        self.main_window.ui.open_output_button.setEnabled(open_output_enabled)

        # Progress bar and status visibility
        if self.main_window.ui.progress_bar and self.main_window.ui.progress_status:
            progress_visible = state == ConversionState.RUNNING
            self.main_window.ui.progress_bar.setVisible(progress_visible)
            self.main_window.ui.progress_status.setVisible(progress_visible)

    def _set_status(self, state: StatusState) -> None:
        """Set the status indicator state."""
        if hasattr(self.main_window, "status_manager") and self.main_window.status_manager:
            self.main_window.status_manager.set_status(state)
