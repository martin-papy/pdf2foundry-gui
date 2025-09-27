"""
Main window for the PDF2Foundry GUI application.

This module contains the MainWindow class which provides the main
user interface for the application.
"""

import logging
from typing import TYPE_CHECKING

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QToolButton,
)

from core.config_manager import ConfigManager
from core.conversion_state import ConversionState
from core.gui_mapping import GuiConfigMapper
from gui.conversion_handler import ConversionHandler
from gui.dialogs.settings import SettingsDialog
from gui.handlers.file_handler import FileHandler
from gui.handlers.output_handler import OutputHandler
from gui.handlers.ui_state_handler import UIStateHandler
from gui.output.output_folder_controller import OutputFolderController
from gui.widgets.drag_drop import DragDropLabel
from gui.widgets.log_console import LogConsole
from gui.widgets.main_window_ui import MainWindowUI
from gui.widgets.notification_manager import NotificationManager
from gui.widgets.status_indicator import StatusManager

if TYPE_CHECKING:
    pass


class MainWindow(QMainWindow):
    """
    Main application window.

    Provides the primary user interface for PDF to Foundry VTT conversion.
    """

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()

        # Initialize configuration
        self.config_manager = ConfigManager()
        self.gui_mapper = GuiConfigMapper()

        # Initialize state tracking
        self._validation_ok = False
        self._current_conversion_state = ConversionState.IDLE

        # Set up the UI
        self.ui = MainWindowUI(self)
        self.setCentralWidget(self.ui)

        # Initialize managers and handlers
        self.notification_manager = NotificationManager(self)
        self.file_handler = FileHandler(self)
        self.output_handler = OutputHandler(self)
        self.ui_state_handler = UIStateHandler(self)

        # Initialize output folder controller
        self.output_folder_controller = OutputFolderController(self.config_manager)

        # Initialize status manager
        if self.ui.status_indicator_widget:
            self.status_manager: StatusManager | None = StatusManager(self.ui.status_indicator_widget)
        else:
            self.status_manager = None

        # Initialize conversion handler
        self.conversion_handler = ConversionHandler(self)

        # Connect signals
        self._connect_signals()

        # Load initial state
        self._load_output_directory()
        self._reset_ui_state()

    def _connect_signals(self) -> None:
        """Connect UI signals to their handlers."""
        # File handling signals
        if self.ui.browse_button:
            self.ui.browse_button.clicked.connect(self.file_handler.on_browse_clicked)

        if self.ui.drag_drop_label:
            self.ui.drag_drop_label.fileAccepted.connect(self.file_handler.on_file_accepted)
            self.ui.drag_drop_label.fileRejected.connect(self.file_handler.on_file_rejected)
            self.ui.drag_drop_label.pdfCleared.connect(self.file_handler.on_pdf_cleared)

        # Output directory signals
        if self.ui.output_dir_selector:
            self.ui.output_dir_selector.pathChanged.connect(self.output_handler.on_output_dir_changed)
            self.ui.output_dir_selector.validityChanged.connect(self.output_handler.on_output_dir_validity_changed)

        # Conversion control signals
        if self.ui.convert_button:
            self.ui.convert_button.clicked.connect(self.on_convert_clicked)
        if self.ui.cancel_button:
            self.ui.cancel_button.clicked.connect(self.on_cancel_clicked)
        if self.ui.open_output_button:
            self.ui.open_output_button.clicked.connect(self.output_handler.on_open_output_clicked)

        # Settings and help signals
        if self.ui.settings_button:
            self.ui.settings_button.clicked.connect(self.on_settings_clicked)
        if self.ui.help_button:
            self.ui.help_button.clicked.connect(self.on_help_clicked)

        # Validation signals
        if self.ui.module_id_input:
            self.ui.module_id_input.textChanged.connect(self.ui_state_handler._on_validation_changed)
        if self.ui.module_title_input:
            self.ui.module_title_input.textChanged.connect(self.ui_state_handler._on_validation_changed)

        # Conversion handler signals - handled directly by the handler

    def _reset_ui_state(self) -> None:
        """Reset UI to initial state."""
        # Reset drag drop label
        if self.ui.drag_drop_label:
            self.ui.drag_drop_label.clearSelectedPdf()

        # Reset status label
        if hasattr(self.ui, "status_label") and self.ui.status_label:
            self.ui.status_label.setText("Ready to convert PDF files")
            self.ui.status_label.setStyleSheet("")  # Clear any styling

        # Reset progress
        if self.ui.progress_bar:
            self.ui.progress_bar.setValue(0)
            self.ui.progress_bar.setVisible(False)

        if self.ui.progress_status:
            self.ui.progress_status.setText("")
            self.ui.progress_status.setVisible(False)

        # Update conversion state
        self.ui_state_handler.set_conversion_state(ConversionState.IDLE)

    def on_convert_clicked(self) -> None:
        """Handle convert button click."""
        if self.conversion_handler:
            self.conversion_handler.start_conversion()

    def on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        if self.conversion_handler:
            self.conversion_handler.cancel_conversion()

    def on_help_clicked(self) -> None:
        """Handle help button click."""
        # Implementation for help functionality
        pass

    def on_settings_clicked(self) -> None:
        """Handle settings button click."""
        dialog = SettingsDialog(self)
        dialog.exec()

    def _load_output_directory(self) -> None:
        """Load the output directory from configuration."""
        if self.ui.output_dir_selector:
            default_path = self.output_folder_controller.current_path()
            self.ui.output_dir_selector.set_path(default_path)

    def _on_conversion_completed(self, result: dict) -> None:
        """Handle conversion completion."""
        # Update last export path
        if "output_path" in result:
            output_path = result["output_path"]
            self.config_manager.set("ui/lastExportPath", output_path)
            logging.getLogger(__name__).info(f"Updated last export path to: {output_path}")

    def set_conversion_state(self, state: ConversionState) -> None:
        """Set the conversion state."""
        self.ui_state_handler.set_conversion_state(state)

    def set_conversion_ui_state(self, state: ConversionState, validation_ok: bool = True) -> None:
        """Set the conversion UI state."""
        self.ui_state_handler.set_conversion_ui_state(state, validation_ok)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event."""
        # Save UI settings
        self.ui.save_ui_settings()

        # Clean up conversion handler
        if hasattr(self, "conversion_handler"):
            self.conversion_handler.cleanup()

        # Clean up notification manager
        if hasattr(self, "notification_manager"):
            self.notification_manager.cleanup()

        event.accept()

    # Property accessors for UI components
    @property
    def status_text(self) -> QLabel | None:
        """Get the status text label."""
        return getattr(self.ui, "status_text", None)

    @property
    def status_dot(self) -> QLabel | None:
        """Get the status dot label."""
        return getattr(self.ui, "status_dot", None)

    @property
    def status_label(self) -> QLabel:
        """Get the status label."""
        if hasattr(self.ui, "status_label") and self.ui.status_label is not None:
            return self.ui.status_label
        raise AttributeError("status_label not found in UI")

    @property
    def output_controller(self) -> "OutputFolderController":
        """Get the output folder controller (alias for backward compatibility)."""
        return self.output_folder_controller

    @property
    def selected_file_path(self) -> str | None:
        """Get the currently selected file path."""
        return self.file_handler.get_selected_pdf_path()

    @property
    def progress_bar(self) -> QProgressBar:
        """Get the progress bar."""
        if not hasattr(self.ui, "progress_bar") or self.ui.progress_bar is None:
            raise AttributeError("progress_bar not found in UI")
        return self.ui.progress_bar

    @property
    def progress_status(self) -> QLabel:
        """Get the progress status label."""
        if not hasattr(self.ui, "progress_status") or self.ui.progress_status is None:
            raise AttributeError("progress_status not found in UI")
        return self.ui.progress_status

    @property
    def log_console(self) -> LogConsole:
        """Get the log console."""
        if not hasattr(self.ui, "log_console") or self.ui.log_console is None:
            raise AttributeError("log_console not found in UI")
        return self.ui.log_console

    @property
    def drag_drop_label(self) -> DragDropLabel | None:
        """Get the drag drop label."""
        return getattr(self.ui, "drag_drop_label", None)

    @property
    def browse_button(self) -> QPushButton | None:
        """Get the browse button."""
        return getattr(self.ui, "browse_button", None)

    @property
    def cancel_button(self) -> QPushButton:
        """Get the cancel button."""
        if not hasattr(self.ui, "cancel_button") or self.ui.cancel_button is None:
            raise AttributeError("cancel_button not found in UI")
        return self.ui.cancel_button

    @property
    def open_output_button(self) -> QToolButton:
        """Get the open output button."""
        if not hasattr(self.ui, "open_output_button") or self.ui.open_output_button is None:
            raise AttributeError("open_output_button not found in UI")
        return self.ui.open_output_button

    @property
    def module_id_input(self) -> QLineEdit:
        """Get the module ID input."""
        if not hasattr(self.ui, "module_id_input") or self.ui.module_id_input is None:
            raise AttributeError("module_id_input not found in UI")
        return self.ui.module_id_input

    @property
    def module_title_input(self) -> QLineEdit:
        """Get the module title input."""
        if not hasattr(self.ui, "module_title_input") or self.ui.module_title_input is None:
            raise AttributeError("module_title_input not found in UI")
        return self.ui.module_title_input

    @property
    def convert_button(self) -> QPushButton:
        """Get the convert button."""
        if not hasattr(self.ui, "convert_button") or self.ui.convert_button is None:
            raise AttributeError("convert_button not found in UI")
        return self.ui.convert_button

    # Legacy API methods for backward compatibility
    def get_selected_pdf_path(self) -> str | None:
        """Get the currently selected PDF file path."""
        return self.file_handler.get_selected_pdf_path()

    def clear_selected_pdf(self) -> None:
        """Clear the currently selected PDF file."""
        self.file_handler.clear_selected_pdf()

    def getSelectedPdfPath(self) -> str:
        """Legacy method for getting selected PDF path."""
        return self.file_handler.getSelectedPdfPath()

    def clearSelectedPdf(self) -> None:
        """Legacy method for clearing selected PDF."""
        self.file_handler.clearSelectedPdf()

    def on_browse_clicked(self) -> None:
        """Handle browse button click (delegated to file handler)."""
        self.file_handler.on_browse_clicked()

    # Delegate methods for backward compatibility with tests
    def _apply_selected_file(self, file_path: str) -> None:
        """Apply selected file (delegated to file handler)."""
        self.file_handler._apply_selected_file(file_path)

    def on_file_accepted(self, file_path: str) -> None:
        """Handle file accepted (delegated to file handler)."""
        self.file_handler.on_file_accepted(file_path)

    def on_file_rejected(self, error_message: str) -> None:
        """Handle file rejected (delegated to file handler)."""
        self.file_handler.on_file_rejected(error_message)

    def on_pdf_selected(self, file_path: str) -> None:
        """Handle PDF selected (delegated to file handler)."""
        self.file_handler.on_file_accepted(file_path)

    def on_pdf_cleared(self) -> None:
        """Handle PDF cleared (delegated to file handler)."""
        self.file_handler.on_pdf_cleared()
