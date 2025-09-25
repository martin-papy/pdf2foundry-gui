"""
Main entry point for the PDF2Foundry GUI application.
"""

import os
import sys
from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths, Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.pdf_utils import is_pdf_file
from gui.widgets.drag_drop import DragDropLabel


class MainWindow(QMainWindow):
    """
    Main application window for PDF2Foundry GUI.

    Provides drag-and-drop PDF upload functionality with status feedback
    and placeholder for future action buttons.
    """

    def __init__(self) -> None:
        super().__init__()

        # State
        self.selected_file_path: str | None = None
        self.last_directory: str | None = None

        # Load settings
        self._load_settings()

        # Set up the main window
        self._setup_window()

        # Create and set up the UI
        self._setup_ui()

        # Connect signals
        self._connect_signals()

        # Set initial focus and tab order
        self._setup_accessibility()

    def _setup_window(self) -> None:
        """Configure the main window properties."""
        self.setWindowTitle("PDF2Foundry")
        self.setMinimumSize(900, 650)

    def _setup_ui(self) -> None:
        """Create and arrange the user interface elements."""
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Create drag-and-drop zone
        self.drag_drop_label = DragDropLabel()
        self.drag_drop_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.drag_drop_label.setMinimumHeight(280)
        self.drag_drop_label.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.drag_drop_label.setAccessibleName("PDF drop zone")

        # Create status label
        self.status_label = QLabel("Drop a PDF file to begin")
        self.status_label.setWordWrap(True)
        self.status_label.setAccessibleName("Status message")
        self.status_label.setAccessibleDescription("Displays the current selection and errors")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Style the status label
        self.status_label.setStyleSheet(
            """
            QLabel {
                color: #666666;
                font-size: 14px;
                padding: 8px;
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 4px;
            }
        """
        )

        # Create button row container with Browse button
        self.button_row = QWidget()
        button_layout = QHBoxLayout(self.button_row)
        button_layout.setContentsMargins(0, 0, 0, 0)

        # Add Browse button
        self.browse_button = QPushButton("Browse…")
        self.browse_button.setToolTip("Choose a PDF file (Ctrl+O)")
        self.browse_button.setAccessibleName("Browse for PDF")
        self.browse_button.setAccessibleDescription("Opens a file dialog filtered to PDF files")
        button_layout.addWidget(self.browse_button)

        # Add stretch to push buttons to the left
        button_layout.addStretch()

        # Add widgets to main layout with appropriate stretch factors
        main_layout.addWidget(self.drag_drop_label)  # Stretch factor 5 (most space)
        main_layout.addWidget(self.status_label)  # Stretch factor 0 (minimal space)
        main_layout.addWidget(self.button_row)  # Stretch factor 0 (minimal space)

        # Set stretch factors for responsive sizing
        main_layout.setStretch(0, 5)  # drag_drop_label gets most space
        main_layout.setStretch(1, 0)  # status_label gets minimal space
        main_layout.setStretch(2, 0)  # button_row gets minimal space

    def _connect_signals(self) -> None:
        """Connect widget signals to their handlers."""
        self.drag_drop_label.fileAccepted.connect(self.on_file_accepted)
        self.drag_drop_label.fileRejected.connect(self.on_file_rejected)
        self.drag_drop_label.pdfSelected.connect(self.on_pdf_selected)
        self.drag_drop_label.pdfCleared.connect(self.on_pdf_cleared)
        self.browse_button.clicked.connect(self.on_browse_clicked)

    def _setup_accessibility(self) -> None:
        """Set up accessibility features and tab order."""
        # Set initial focus to the drag-drop area
        self.drag_drop_label.setFocus()

        # Set tab order: drag-drop -> status -> browse button
        self.setTabOrder(self.drag_drop_label, self.status_label)
        self.setTabOrder(self.status_label, self.browse_button)

    def _load_settings(self) -> None:
        """Load application settings."""
        settings = QSettings("PDF2Foundry", "GUI")
        last_dir = settings.value("ui/last_open_dir", None)
        self.last_directory = str(last_dir) if last_dir is not None else None

    def _save_settings(self) -> None:
        """Save application settings."""
        settings = QSettings("PDF2Foundry", "GUI")
        if self.last_directory:
            settings.setValue("ui/last_open_dir", self.last_directory)

    def on_browse_clicked(self) -> None:
        """Handle Browse button click to open file dialog."""
        # Determine starting directory
        if self.last_directory and os.path.exists(self.last_directory):
            start_dir = self.last_directory
        else:
            # Fallback to user's Documents directory
            start_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)

        # Open file dialog with PDF filter
        file_path, _ = QFileDialog.getOpenFileName(self, "Select PDF", start_dir, "PDF Files (*.pdf)")

        # Handle cancellation (empty path)
        if not file_path:
            return

        # Update last directory for future dialogs
        self.last_directory = os.path.dirname(file_path)
        self._save_settings()

        # Validate the selected file
        path_obj = Path(file_path)
        if is_pdf_file(path_obj):
            # Valid PDF - use unified file selection flow
            self._apply_selected_file(file_path)
        else:
            # Invalid file - show error through existing rejection handler
            self.on_file_rejected("Not a valid PDF file")

    def on_pdf_selected(self, path: str) -> None:
        """
        Handle PDF selection signal from drag-drop widget.

        Args:
            path: Path to the selected PDF file
        """
        # This signal is emitted alongside fileAccepted, so we don't need
        # to duplicate the logic here. It's available for external connections.
        pass

    def on_pdf_cleared(self) -> None:
        """Handle PDF cleared signal from drag-drop widget."""
        self.selected_file_path = None
        self.status_label.setText("Drop a PDF file to begin")

        # Reset status label styling to default
        self.status_label.setStyleSheet(
            """
            QLabel {
                color: #666666;
                font-size: 14px;
                padding: 8px;
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 4px;
            }
        """
        )

    def getSelectedPdfPath(self) -> str:
        """
        Get the currently selected PDF path.

        Returns:
            The absolute path to the selected PDF file, or empty string if none selected.
        """
        return self.selected_file_path or ""

    def clearSelectedPdf(self) -> None:
        """Clear the current PDF selection."""
        self.drag_drop_label.clearSelectedPdf()
        # The on_pdf_cleared handler will be called automatically

    def _apply_selected_file(self, path: str) -> None:
        """
        Apply a selected file to the application state.

        Used by both drag-and-drop and future Browse button flows.

        Args:
            path: Path to the selected PDF file
        """
        self.selected_file_path = path

        # Update drag-drop widget to show selected state
        self.drag_drop_label.set_file_selected(path)

    def on_file_accepted(self, path: str) -> None:
        """
        Handle successful file selection from drag-and-drop.

        Args:
            path: Path to the accepted PDF file
        """
        self._apply_selected_file(path)

        # Update status with success message
        filename = os.path.basename(path)
        self.status_label.setText(f"Selected: {filename}")

        # Apply success styling
        self.status_label.setStyleSheet(
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

    def on_file_rejected(self, message: str) -> None:
        """
        Handle file rejection from drag-and-drop.

        Args:
            message: Error message describing why the file was rejected
        """
        self.selected_file_path = None

        # Update status with error message
        self.status_label.setText(message)

        # Apply error styling
        self.status_label.setStyleSheet(
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


def main() -> int:
    """Main application entry point."""
    app = QApplication(sys.argv)

    # Create and show the main window
    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
