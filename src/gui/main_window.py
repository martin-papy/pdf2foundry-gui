"""
Main window for the PDF2Foundry GUI application.

This module contains the MainWindow class which provides the main
user interface for the application.
"""

import logging
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.config_manager import ConfigManager
from core.gui_mapping import GuiConfigMapper
from core.pdf_utils import is_pdf_file
from gui.conversion_handler import ConversionHandler
from gui.widgets.drag_drop import DragDropLabel


class MainWindow(QMainWindow):
    """
    Main application window for PDF2Foundry GUI.

    Provides drag-and-drop PDF upload functionality with status feedback
    and placeholder for future action buttons.
    """

    def __init__(self) -> None:
        super().__init__()

        # Configuration management
        self._config_manager = ConfigManager()
        self._gui_mapper = GuiConfigMapper()
        self._logger = logging.getLogger(__name__)

        # Conversion management
        self._conversion_handler = ConversionHandler(self)

        # File state
        self.selected_file_path: str | None = None

        # UI components (will be created in _setup_ui)
        self.drag_drop_label: DragDropLabel
        self.status_label: QLabel
        self.browse_button: QPushButton
        self.module_id_input: QLineEdit
        self.module_title_input: QLineEdit
        self.convert_button: QPushButton
        self.cancel_button: QPushButton
        self.progress_bar: QProgressBar
        self.progress_status: QLabel
        self.log_text: QTextEdit

        # Initialize UI
        self._setup_window()
        self._setup_ui()
        self._connect_signals()
        self._setup_accessibility()
        self._load_settings()

        # Connect to application quit signal for cleanup
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._on_application_quit)

    def _setup_window(self) -> None:
        """Configure main window properties."""
        self.setWindowTitle("PDF2Foundry GUI")
        self.resize(800, 600)

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Create drag and drop area
        self.drag_drop_label = DragDropLabel()
        main_layout.addWidget(self.drag_drop_label, stretch=3)

        # Create status label
        self.status_label = QLabel("Ready to convert PDF files")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setAccessibleName("Status message")
        self.status_label.setAccessibleDescription("Displays the current selection and errors")
        self.status_label.setStyleSheet(
            """
            QLabel {
                font-size: 14px;
                padding: 10px;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
        """
        )
        main_layout.addWidget(self.status_label, stretch=0)

        # Create button row with browse button
        button_row = self._create_button_row()
        main_layout.addWidget(button_row, stretch=0)

        # Create conversion controls
        conversion_controls = self._create_conversion_controls()
        main_layout.addWidget(conversion_controls, stretch=0)

        # Create progress section
        progress_section = self._create_progress_section()
        main_layout.addWidget(progress_section, stretch=0)

        # Create log section
        log_section = self._create_log_section()
        main_layout.addWidget(log_section, stretch=2)

    def _create_button_row(self) -> QWidget:
        """Create the button row with browse functionality."""
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)

        # Add stretch to center the button
        button_layout.addStretch()

        # Browse button
        self.browse_button = QPushButton("Browse…")
        self.browse_button.setMinimumHeight(40)
        self.browse_button.clicked.connect(self.on_browse_clicked)
        self.browse_button.setToolTip("Choose a PDF file (Ctrl+O)")
        self.browse_button.setAccessibleName("Browse for PDF")
        self.browse_button.setAccessibleDescription("Opens a file dialog filtered to PDF files")
        button_layout.addWidget(self.browse_button)

        # Add stretch to center the button
        button_layout.addStretch()

        return button_widget

    def _create_conversion_controls(self) -> QWidget:
        """Create conversion input controls."""
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(10)

        # Module ID input
        mod_id_layout = QHBoxLayout()
        mod_id_label = QLabel("Module ID:")
        mod_id_label.setMinimumWidth(100)
        self.module_id_input = QLineEdit()
        self.module_id_input.setPlaceholderText("e.g., my-adventure-module")
        self.module_id_input.textChanged.connect(self._conversion_handler.validate_inputs)
        mod_id_layout.addWidget(mod_id_label)
        mod_id_layout.addWidget(self.module_id_input)
        controls_layout.addLayout(mod_id_layout)

        # Module title input
        mod_title_layout = QHBoxLayout()
        mod_title_label = QLabel("Module Title:")
        mod_title_label.setMinimumWidth(100)
        self.module_title_input = QLineEdit()
        self.module_title_input.setPlaceholderText("e.g., My Adventure Module")
        self.module_title_input.textChanged.connect(self._conversion_handler.validate_inputs)
        mod_title_layout.addWidget(mod_title_label)
        mod_title_layout.addWidget(self.module_title_input)
        controls_layout.addLayout(mod_title_layout)

        # Convert and cancel buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.convert_button = QPushButton("Convert to Foundry")
        self.convert_button.setMinimumHeight(40)
        self.convert_button.setEnabled(False)
        self.convert_button.clicked.connect(self._conversion_handler.start_conversion)
        button_layout.addWidget(self.convert_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMinimumHeight(40)
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._conversion_handler.cancel_conversion)
        button_layout.addWidget(self.cancel_button)

        button_layout.addStretch()
        controls_layout.addLayout(button_layout)

        return controls_widget

    def _create_progress_section(self) -> QWidget:
        """Create progress tracking section."""
        progress_widget = QWidget()
        progress_layout = QVBoxLayout(progress_widget)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(5)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)

        # Progress status
        self.progress_status = QLabel()
        self.progress_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_status.setVisible(False)
        self.progress_status.setStyleSheet("QLabel { font-style: italic; color: #666; }")
        progress_layout.addWidget(self.progress_status)

        return progress_widget

    def _create_log_section(self) -> QWidget:
        """Create log output section."""
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.setSpacing(5)

        # Log label
        log_label = QLabel("Conversion Log:")
        log_label.setStyleSheet("QLabel { font-weight: bold; }")
        log_layout.addWidget(log_label)

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        self.log_text.setStyleSheet(
            """
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
            }
        """
        )
        log_layout.addWidget(self.log_text)

        return log_widget

    def _connect_signals(self) -> None:
        """Connect widget signals to handlers."""
        # Connect drag-drop signals
        self.drag_drop_label.fileAccepted.connect(self.on_file_accepted)
        self.drag_drop_label.fileRejected.connect(self.on_file_rejected)
        self.drag_drop_label.pdfSelected.connect(self.on_pdf_selected)
        self.drag_drop_label.pdfCleared.connect(self.on_pdf_cleared)

    def _setup_accessibility(self) -> None:
        """Set up accessibility features."""
        # Set initial focus to drag-drop area
        self.drag_drop_label.setFocus()

        # Set tab order for keyboard navigation
        self.setTabOrder(self.drag_drop_label, self.module_id_input)
        self.setTabOrder(self.module_id_input, self.module_title_input)
        self.setTabOrder(self.module_title_input, self.convert_button)
        self.setTabOrder(self.convert_button, self.cancel_button)

    def _load_settings(self) -> None:
        """Load settings from configuration."""
        pass  # Placeholder for future settings loading

    def _save_settings(self) -> None:
        """Save settings to configuration."""
        pass  # Placeholder for future settings saving

    def on_browse_clicked(self) -> None:
        """Handle browse button click."""
        # Get the last used directory or default to Documents
        last_dir = self._config_manager.get("last_browse_directory", "")
        if not last_dir:
            last_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)

        # Show file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PDF File",
            last_dir,
            "PDF Files (*.pdf);;All Files (*)",
        )

        if file_path:
            # Save the directory for next time
            self._config_manager.set("last_browse_directory", str(Path(file_path).parent))

            # Validate and apply the file
            if is_pdf_file(Path(file_path)):
                self._apply_selected_file(file_path)
            else:
                self.on_file_rejected("Selected file is not a valid PDF")

    def on_pdf_selected(self, path: str) -> None:
        """Handle PDF selection from drag-drop or browse."""
        self._apply_selected_file(path)

    def on_pdf_cleared(self) -> None:
        """Handle PDF clearing."""
        self.selected_file_path = None
        self.status_label.setText("Ready to convert PDF files")
        self.status_label.setStyleSheet(
            """
            QLabel {
                font-size: 14px;
                padding: 10px;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
        """
        )
        self._conversion_handler.validate_inputs()

    def getSelectedPdfPath(self) -> str:
        """Get the currently selected PDF path (for API compatibility)."""
        return self.selected_file_path or ""

    def clearSelectedPdf(self) -> None:
        """Clear the selected PDF (for API compatibility)."""
        self.selected_file_path = None
        self.drag_drop_label.reset()

    def _apply_selected_file(self, path: str) -> None:
        """Apply a selected file to the UI."""
        self.selected_file_path = path
        file_name = Path(path).name

        # Update status
        self.status_label.setText(f"Selected: {file_name}")
        self.status_label.setStyleSheet(
            """
            QLabel {
                color: #155724;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                background-color: #d4edda;
                border: 1px solid #c3e6cb;
                border-radius: 4px;
            }
        """
        )

        # Validate inputs to update button state
        self._conversion_handler.validate_inputs()

    def on_file_accepted(self, path: str) -> None:
        """Handle successful file acceptance."""
        self._apply_selected_file(path)

    def on_file_rejected(self, message: str) -> None:
        """Handle file rejection."""
        self.status_label.setText(f"Error: {message}")
        self.status_label.setStyleSheet(
            """
            QLabel {
                color: #721c24;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                background-color: #f8d7da;
                border: 1px solid #f5c6cb;
                border-radius: 4px;
            }
        """
        )

    def _on_application_quit(self) -> None:
        """Handle application shutdown gracefully."""
        self._conversion_handler.shutdown(timeout_ms=2000)
