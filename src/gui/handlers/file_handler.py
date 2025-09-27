"""
File handling functionality for the main window.

This module contains methods for handling PDF file selection,
validation, and related UI updates.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QFileDialog

from core.pdf_utils import is_pdf_file

if TYPE_CHECKING:
    from gui.main_window import MainWindow


class FileHandler:
    """Handles file-related operations for the main window."""

    def __init__(self, main_window: "MainWindow") -> None:
        """Initialize the file handler."""
        self.main_window = main_window
        self._logger = logging.getLogger(__name__)

    def on_browse_clicked(self) -> None:
        """Handle browse button click to select PDF file."""
        # Get the last used directory from settings
        last_dir = self.main_window.config_manager.get("ui/lastPdfDirectory", "")

        # Fallback to Documents folder if no last directory
        if not last_dir:
            last_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)

        file_path, _ = QFileDialog.getOpenFileName(
            self.main_window, "Select PDF File", last_dir, "PDF Files (*.pdf);;All Files (*)"
        )

        if file_path:
            # Save the directory for next time
            directory = str(Path(file_path).parent)
            self.main_window.config_manager.set("ui/lastPdfDirectory", directory)

            # Validate and apply the file
            if is_pdf_file(Path(file_path)):
                self._apply_selected_file(file_path)
            else:
                self._logger.warning("File rejected: Selected file is not a valid PDF")
                if self.main_window.drag_drop_label:
                    self.main_window.drag_drop_label.set_error("Selected file is not a valid PDF")

    def on_file_accepted(self, file_path: str) -> None:
        """Handle accepted file from drag and drop."""
        # Call the main window's delegate method for backward compatibility
        self.main_window._apply_selected_file(file_path)

    def on_file_rejected(self, error_message: str) -> None:
        """Handle rejected file from drag and drop."""
        self._logger.warning(f"File rejected: {error_message}")

        # Update status label
        if hasattr(self.main_window, "status_label") and self.main_window.status_label:
            self.main_window.status_label.setText(f"Error: {error_message}")
            # Apply error styling (accessible colors)
            self.main_window.status_label.setStyleSheet("background-color: #f8d7da; color: #721c24;")

        # The drag drop widget will handle showing the error

    def on_pdf_cleared(self) -> None:
        """Handle PDF file being cleared."""
        self._logger.info("PDF file cleared")
        self.main_window._reset_ui_state()

    def on_pdf_selected(self, file_path: str) -> None:
        """Handle PDF file being selected."""
        self._apply_selected_file(file_path)

    def _apply_selected_file(self, file_path: str) -> None:
        """Apply the selected PDF file to the UI."""
        self._logger.info(f"PDF file selected: {file_path}")

        # Update the drag drop label
        if self.main_window.drag_drop_label:
            self.main_window.drag_drop_label.set_file_selected(file_path)

        # Update status label
        if hasattr(self.main_window, "status_label") and self.main_window.status_label:
            filename = Path(file_path).name
            self.main_window.status_label.setText(f"Selected: {filename}")
            # Apply success styling (accessible colors)
            self.main_window.status_label.setStyleSheet("background-color: #f8f9fa; color: #198754;")

        # Update validation state
        self.main_window.ui_state_handler._on_validation_changed()

        # Update convert button state
        self.main_window.ui_state_handler._update_convert_button_state()

    def get_selected_pdf_path(self) -> str | None:
        """Get the currently selected PDF file path."""
        if self.main_window.drag_drop_label:
            path = self.main_window.drag_drop_label.selectedPdfPath()
            return path if path else None
        return None

    def clear_selected_pdf(self) -> None:
        """Clear the currently selected PDF file."""
        if self.main_window.drag_drop_label:
            self.main_window.drag_drop_label.clearSelectedPdf()

    # Legacy API compatibility methods
    def getSelectedPdfPath(self) -> str:
        """Legacy method for getting selected PDF path."""
        return self.get_selected_pdf_path() or ""

    def clearSelectedPdf(self) -> None:
        """Legacy method for clearing selected PDF."""
        self.clear_selected_pdf()
