"""
Main window for the PDF2Foundry GUI application.

This module contains the MainWindow class which provides the main
user interface for the application.
"""

import logging
from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow

from core.config_manager import ConfigManager
from core.gui_mapping import GuiConfigMapper
from core.pdf_utils import is_pdf_file
from gui.conversion_handler import ConversionHandler
from gui.utils.styling import apply_status_style
from gui.widgets.main_window_ui import MainWindowUI


class MainWindow(QMainWindow):
    """
    Main application window.

    Provides the primary user interface for PDF to Foundry VTT conversion.
    """

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()

        # Initialize UI
        self.ui = MainWindowUI(self)
        self.ui.setup_ui()

        # Initialize components
        self.config_manager = ConfigManager()
        self.gui_mapper = GuiConfigMapper()

        # Initialize conversion handler
        self.conversion_handler = ConversionHandler(self)

        # Connect signals
        self._connect_signals()

        # Set initial state
        self._reset_ui_state()

    def _connect_signals(self) -> None:
        """Connect UI signals to handlers."""
        if not self.ui.drag_drop_label or not self.ui.browse_button:
            return

        # File selection signals
        self.ui.drag_drop_label.fileAccepted.connect(self.on_file_accepted)
        self.ui.drag_drop_label.fileRejected.connect(self.on_file_rejected)
        self.ui.drag_drop_label.pdfCleared.connect(self.on_pdf_cleared)
        self.ui.browse_button.clicked.connect(self.on_browse_clicked)

    def _reset_ui_state(self) -> None:
        """Reset UI to initial state."""
        if self.ui.status_manager:
            self.ui.status_manager.reset_to_idle()

        if self.ui.status_label:
            self.ui.status_label.setText("Ready to convert PDF files")
            apply_status_style(self.ui.status_label, "default")

        if self.ui.progress_bar:
            self.ui.progress_bar.setVisible(False)
            self.ui.progress_bar.setValue(0)

        if self.ui.progress_status:
            self.ui.progress_status.setVisible(False)
            self.ui.progress_status.clear()

    def on_browse_clicked(self) -> None:
        """Handle browse button click."""
        settings = QSettings()
        last_dir = settings.value("ui/lastDirectory", str(Path.home()))

        file_path, _ = QFileDialog.getOpenFileName(self, "Select PDF File", last_dir, "PDF Files (*.pdf);;All Files (*)")

        if file_path:
            # Save directory for next time
            settings.setValue("ui/lastDirectory", str(Path(file_path).parent))

            if is_pdf_file(file_path):
                self._apply_selected_file(file_path)
            else:
                if self.ui.drag_drop_label:
                    self.ui.drag_drop_label.set_error("Selected file is not a valid PDF")

    def on_file_accepted(self, file_path: str) -> None:
        """Handle file acceptance from drag and drop."""
        self._apply_selected_file(file_path)

    def on_file_rejected(self, error_message: str) -> None:
        """Handle file rejection from drag and drop."""
        logging.warning(f"File rejected: {error_message}")
        if self.ui.status_label:
            self.ui.status_label.setText(f"File rejected: {error_message}")
            apply_status_style(self.ui.status_label, "error")

    def on_pdf_cleared(self) -> None:
        """Handle PDF file being cleared."""
        self._reset_ui_state()
        logging.info("PDF file cleared")

    def _apply_selected_file(self, file_path: str) -> None:
        """Apply the selected file to the UI."""
        if not self.ui.drag_drop_label or not self.ui.status_label:
            return

        self.ui.drag_drop_label.set_file_selected(file_path)

        # Update status
        file_name = Path(file_path).name
        self.ui.status_label.setText(f"Selected: {file_name}")
        apply_status_style(self.ui.status_label, "success")

        if self.ui.status_manager:
            self.ui.status_manager.reset_to_idle()

        logging.info(f"PDF file selected: {file_path}")

    def get_selected_pdf_path(self) -> str:
        """Get the currently selected PDF path."""
        if self.ui.drag_drop_label:
            return self.ui.drag_drop_label.get_selected_pdf_path()
        return ""

    def clear_selected_pdf(self) -> None:
        """Clear the currently selected PDF."""
        if self.ui.drag_drop_label:
            self.ui.drag_drop_label.reset()

    def closeEvent(self, event) -> None:
        """Handle window close event."""
        # Save UI settings
        self.ui.save_ui_settings()

        # Clean up conversion handler
        if hasattr(self, "conversion_handler"):
            self.conversion_handler.cleanup()

        event.accept()


def main() -> None:
    """Main entry point for the GUI application."""
    app = QApplication([])
    app.setApplicationName("PDF2Foundry GUI")
    app.setOrganizationName("PDF2Foundry")

    # Set application icon if available
    # app.setWindowIcon(QIcon("path/to/icon.png"))

    window = MainWindow()
    window.show()

    return app.exec()
