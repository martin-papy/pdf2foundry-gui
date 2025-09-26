"""
Main window for the PDF2Foundry GUI application.

This module contains the MainWindow class which provides the main
user interface for the application.
"""

import logging
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
)

from core.config_manager import ConfigManager
from core.gui_mapping import GuiConfigMapper
from core.pdf_utils import is_pdf_file
from gui.conversion_handler import ConversionHandler
from gui.dialogs.settings import SettingsDialog
from gui.utils.styling import apply_status_style
from gui.widgets.drag_drop import DragDropLabel
from gui.widgets.log_console import LogConsole
from gui.widgets.main_window_ui import MainWindowUI
from gui.widgets.status_indicator import StatusState


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
        self._config_manager = self.config_manager  # Backward compatibility alias
        self.gui_mapper = GuiConfigMapper()
        self._gui_mapper = self.gui_mapper  # Backward compatibility alias

        # Initialize conversion handler
        self.conversion_handler = ConversionHandler(self)

        # Connect signals
        self._connect_signals()

        # Load output directory from config
        self._load_output_directory()

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

        # Header button signals
        if self.ui.help_button:
            self.ui.help_button.clicked.connect(self.on_help_clicked)
        if self.ui.settings_button:
            self.ui.settings_button.clicked.connect(self.on_settings_clicked)

        # Output directory selector signals
        if self.ui.output_dir_selector:
            self.ui.output_dir_selector.pathChanged.connect(self.on_output_dir_changed)
            self.ui.output_dir_selector.validityChanged.connect(self.on_output_dir_validity_changed)

    def _reset_ui_state(self) -> None:
        """Reset UI to initial state."""
        # Clear selected file
        if self.ui.drag_drop_label:
            self.ui.drag_drop_label.clearSelectedPdf()

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

        # Update convert button state
        self._update_convert_button_state()

    def on_browse_clicked(self) -> None:
        """Handle browse button click."""
        # Get last directory from config manager, fallback to Documents
        last_dir = self._config_manager.get("ui/lastDirectory", "")
        if not last_dir:
            default_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation) or str(
                Path.home()
            )
            last_dir = default_dir

        file_path, _ = QFileDialog.getOpenFileName(self, "Select PDF File", last_dir, "PDF Files (*.pdf);;All Files (*)")

        if file_path:
            # Save directory for next time
            self._config_manager.set("ui/lastDirectory", str(Path(file_path).parent))

            if is_pdf_file(Path(file_path)):
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
        # Clear selected file path
        self._reset_ui_state()
        if self.ui.status_label:
            self.ui.status_label.setText(f"Error: {error_message}")
            apply_status_style(self.ui.status_label, "error")

    def on_pdf_cleared(self) -> None:
        """Handle PDF file being cleared."""
        self._reset_ui_state()
        logging.info("PDF file cleared")

    def on_pdf_selected(self, file_path: str) -> None:
        """Handle PDF file being selected (for test compatibility)."""
        self._apply_selected_file(file_path)

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

        # Update convert button state based on both PDF selection and output directory validity
        self._update_convert_button_state()

        logging.info(f"PDF file selected: {file_path}")

    def on_help_clicked(self) -> None:
        """Handle help button click."""
        # Create About dialog
        about_text = """
        <h3>PDF2Foundry GUI</h3>
        <p>A desktop application for converting PDF files to Foundry VTT modules.</p>
        <p><b>Version:</b> 1.0.0</p>
        <p><b>Links:</b></p>
        <ul>
        <li><a href="https://github.com/pdf2foundry/pdf2foundry">Documentation</a></li>
        <li><a href="https://github.com/pdf2foundry/pdf2foundry/releases">Release Notes</a></li>
        <li><a href="https://github.com/pdf2foundry/pdf2foundry/issues">Report Issue</a></li>
        </ul>
        """

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("About PDF2Foundry GUI")
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText(about_text)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)

        # Handle link clicks
        msg_box.setTextInteractionFlags(msg_box.textInteractionFlags() | Qt.TextInteractionFlag.TextSelectableByMouse)

        # Connect link activation
        def on_link_activated(link: str) -> None:
            QDesktopServices.openUrl(QUrl(link))

        # Note: QMessageBox doesn't directly support linkActivated, but we can handle it through the text
        msg_box.exec()

    def on_settings_clicked(self) -> None:
        """Handle settings button click."""
        settings_dialog = SettingsDialog(self)
        if settings_dialog.exec() == SettingsDialog.DialogCode.Accepted:
            # Settings were saved, refresh any settings-dependent UI
            logging.info("Settings updated")
            # Refresh output directory display from updated config
            self._load_output_directory()

    def _load_output_directory(self) -> None:
        """Load output directory from config and update the UI."""
        if not self.ui.output_dir_selector:
            return

        # Get output directory from config
        output_dir = self.config_manager.get("output_dir", "")

        if output_dir:
            self.ui.output_dir_selector.set_path(output_dir)
        # If no config value, the OutputDirectorySelector will use its default

    def on_output_dir_changed(self, path: str) -> None:
        """Handle output directory path changes."""
        # Save to config manager
        self.config_manager.set("output_dir", path)
        logging.info(f"Output directory changed to: {path}")

    def on_output_dir_validity_changed(self, is_valid: bool, error_message: str) -> None:
        """Handle output directory validity changes."""
        if not is_valid and error_message:
            logging.warning(f"Output directory validation error: {error_message}")

        # Update convert button state
        self._update_convert_button_state()

    def _update_convert_button_state(self) -> None:
        """Update convert button enabled state based on PDF selection and output directory validity."""
        if not self.ui.convert_button:
            return

        # Check if we have a valid PDF
        has_pdf = bool(self.get_selected_pdf_path())

        # Check if output directory is valid
        output_dir_valid = True
        if self.ui.output_dir_selector:
            output_dir_valid = self.ui.output_dir_selector.is_valid()

        # Enable convert button only if both conditions are met
        self.ui.convert_button.setEnabled(has_pdf and output_dir_valid)

    def get_selected_pdf_path(self) -> str | None:
        """Get the currently selected PDF path."""
        if self.ui.drag_drop_label:
            path = self.ui.drag_drop_label.selectedPdfPath()
            return path if path else None
        return None

    def clear_selected_pdf(self) -> None:
        """Clear the currently selected PDF."""
        if self.ui.drag_drop_label:
            self.ui.drag_drop_label.clearSelectedPdf()

    # Backward compatibility methods for tests (camelCase)
    def getSelectedPdfPath(self) -> str:
        """Get the currently selected PDF path (camelCase for compatibility)."""
        path = self.get_selected_pdf_path()
        return path if path is not None else ""

    def clearSelectedPdf(self) -> None:
        """Clear the currently selected PDF (camelCase for compatibility)."""
        self.clear_selected_pdf()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event."""
        # Save UI settings
        self.ui.save_ui_settings()

        # Clean up conversion handler
        if hasattr(self, "conversion_handler"):
            self.conversion_handler.cleanup()

        event.accept()

    # Properties for backward compatibility with tests
    @property
    def status_text(self) -> QLabel | None:
        """Get the status text widget."""
        return self.ui.status_indicator.status_text if self.ui.status_indicator else None

    @property
    def status_dot(self) -> QLabel | None:
        """Get the status dot widget."""
        return self.ui.status_indicator.status_dot if self.ui.status_indicator else None

    @property
    def status_label(self) -> QLabel:
        """Get the status label widget."""
        assert self.ui.status_label is not None, "Status label not initialized"
        return self.ui.status_label

    @property
    def progress_bar(self) -> QProgressBar:
        """Get the progress bar widget."""
        assert self.ui.progress_bar is not None, "Progress bar not initialized"
        return self.ui.progress_bar

    @property
    def progress_status(self) -> QLabel:
        """Get the progress status widget."""
        assert self.ui.progress_status is not None, "Progress status not initialized"
        return self.ui.progress_status

    @property
    def log_console(self) -> LogConsole:
        """Get the log console widget."""
        assert self.ui.log_console is not None, "Log console not initialized"
        return self.ui.log_console

    @property
    def drag_drop_label(self) -> DragDropLabel | None:
        """Get the drag drop label widget."""
        return self.ui.drag_drop_label

    @property
    def browse_button(self) -> QPushButton | None:
        """Get the browse button widget."""
        return self.ui.browse_button

    @property
    def cancel_button(self) -> object:
        """Get the cancel button widget (placeholder for compatibility)."""

        # For now, return a mock object that has setEnabled method
        class MockButton:
            def setEnabled(self, enabled: bool) -> None:
                pass

        return MockButton()

    @property
    def selected_file_path(self) -> str | None:
        """Get the selected file path."""
        return self.get_selected_pdf_path()

    @property
    def module_id_input(self) -> QLineEdit:
        """Get the module ID input widget."""
        assert self.ui.module_id_input is not None, "Module ID input not initialized"
        return self.ui.module_id_input

    @property
    def module_title_input(self) -> QLineEdit:
        """Get the module title input widget."""
        assert self.ui.module_title_input is not None, "Module title input not initialized"
        return self.ui.module_title_input

    @property
    def convert_button(self) -> QPushButton:
        """Get the convert button widget."""
        assert self.ui.convert_button is not None, "Convert button not initialized"
        return self.ui.convert_button

    def _set_status(self, state: StatusState) -> None:
        """Set the status indicator state (compatibility method)."""
        if self.ui.status_manager:
            self.ui.status_manager.set_status(state)


def main() -> int:
    """Main entry point for the GUI application."""
    app = QApplication([])
    app.setApplicationName("PDF2Foundry GUI")
    app.setOrganizationName("PDF2Foundry")

    # Set application icon if available
    # app.setWindowIcon(QIcon("path/to/icon.png"))

    window = MainWindow()
    window.show()

    return app.exec()
