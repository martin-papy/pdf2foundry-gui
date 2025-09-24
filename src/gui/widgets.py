"""
Custom widgets for the PDF2Foundry GUI application.
"""

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent, QKeyEvent
from PySide6.QtWidgets import QLabel, QSizePolicy, QWidget

from core.pdf_utils import extract_local_paths_from_mimedata, validate_single_pdf_source


class DragDropLabel(QLabel):
    """
    Custom QLabel widget for drag-and-drop PDF file selection.

    Provides visual feedback for different states and emits signals
    for accepted/rejected files.
    """

    # Signals
    fileAccepted = Signal(str)  # Emitted with file path when a valid PDF is dropped
    fileRejected = Signal(str)  # Emitted with error message when invalid file is dropped

    # Visual states
    STATE_NORMAL = "normal"
    STATE_HOVER = "hover"
    STATE_REJECT = "reject"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Enable drag and drop
        self.setAcceptDrops(True)

        # Set up initial appearance
        self._current_state = self.STATE_NORMAL
        self._setup_appearance()

        # Make focusable for accessibility
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Set accessibility properties
        self.setAccessibleName("PDF file drop zone")
        self.setAccessibleDescription("Drag and drop a PDF file here, or use the Browse button")

    def _setup_appearance(self) -> None:
        """Set up the initial appearance and styling."""
        # Set size policy to expand
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Set minimum size
        self.setMinimumSize(400, 200)

        # Center alignment
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Set initial text and styling
        self._update_appearance()

    def _update_appearance(self) -> None:
        """Update appearance based on current state."""
        if self._current_state == self.STATE_NORMAL:
            self.setStyleSheet(
                """
                QLabel {
                    border: 2px dashed #cccccc;
                    border-radius: 8px;
                    background-color: #fafafa;
                    color: #666666;
                    font-size: 16px;
                    padding: 20px;
                }
            """
            )
            self.setText("📂 Drag & Drop your PDF here\n\nOR\n\nUse the Browse button below")

        elif self._current_state == self.STATE_HOVER:
            self.setStyleSheet(
                """
                QLabel {
                    border: 2px dashed #0078d4;
                    border-radius: 8px;
                    background-color: #f0f8ff;
                    color: #0078d4;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 20px;
                }
            """
            )
            self.setText("📂 Drop your PDF file here")

        elif self._current_state == self.STATE_REJECT:
            self.setStyleSheet(
                """
                QLabel {
                    border: 2px dashed #d13438;
                    border-radius: 8px;
                    background-color: #fdf2f2;
                    color: #d13438;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 20px;
                }
            """
            )
            # Text will be set by the rejection handler

        # Update cursor
        if self._current_state == self.STATE_HOVER:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def _set_state(self, state: str) -> None:
        """Change the visual state and update appearance."""
        if self._current_state != state:
            self._current_state = state
            self._update_appearance()

    def _reset_to_normal_delayed(self) -> None:
        """Reset to normal state after a short delay (for reject state)."""
        from PySide6.QtCore import QTimer

        QTimer.singleShot(3000, lambda: self._set_state(self.STATE_NORMAL))

    # Drag and drop event handlers

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter events."""
        if event.mimeData().hasUrls():
            # Check if we can potentially accept this
            try:
                paths = extract_local_paths_from_mimedata(event.mimeData())
                valid_path, error_message = validate_single_pdf_source(paths)
                if valid_path:
                    event.acceptProposedAction()
                    self._set_state(self.STATE_HOVER)
                    return
                else:
                    # Validation failed - reject with specific error
                    event.ignore()
                    self._set_state(self.STATE_REJECT)
                    self.setText(f"❌ {error_message or 'Invalid file'}\n\nPlease select a valid PDF file")
                    self._reset_to_normal_delayed()
                    return
            except Exception:
                pass

        # Reject the drag (no URLs or exception occurred)
        event.ignore()
        self._set_state(self.STATE_REJECT)
        self.setText("❌ Invalid file type\n\nOnly PDF files are supported")
        self._reset_to_normal_delayed()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        """Handle drag move events."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        """Handle drag leave events."""
        self._set_state(self.STATE_NORMAL)
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop events."""
        try:
            # Extract and validate the dropped files
            paths = extract_local_paths_from_mimedata(event.mimeData())
            valid_path, error_message = validate_single_pdf_source(paths)

            if valid_path:
                # Success - emit signal with the file path
                self.fileAccepted.emit(str(valid_path))
                self._set_state(self.STATE_NORMAL)
                self.setText(f"✅ PDF Selected:\n{valid_path.name}\n\nReady to convert!")
                event.acceptProposedAction()
            else:
                # Validation failed - show error
                self._handle_rejection(error_message or "Invalid file")
                event.ignore()

        except Exception as e:
            # Unexpected error
            self._handle_rejection(f"Error processing file: {e!s}")
            event.ignore()

    def _handle_rejection(self, error_message: str) -> None:
        """Handle file rejection with visual feedback."""
        self._set_state(self.STATE_REJECT)
        self.setText(f"❌ {error_message}\n\nPlease select a valid PDF file")
        self.fileRejected.emit(error_message)
        self._reset_to_normal_delayed()

    # Keyboard accessibility

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle keyboard events for accessibility."""
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            # Simulate a click to trigger file browser (will be handled by parent)
            self.clicked.emit() if hasattr(self, "clicked") else None
        else:
            super().keyPressEvent(event)

    # Public methods for external control

    def reset(self) -> None:
        """Reset the widget to its initial state."""
        self._set_state(self.STATE_NORMAL)

    def set_file_selected(self, file_path: str) -> None:
        """Update the widget to show a selected file."""
        path = Path(file_path)
        self._set_state(self.STATE_NORMAL)
        self.setText(f"✅ PDF Selected:\n{path.name}\n\nReady to convert!")

    def set_error(self, error_message: str) -> None:
        """Show an error state with custom message."""
        self._handle_rejection(error_message)

    # Size hints for proper layout

    def sizeHint(self) -> QSize:
        """Provide size hint for layout managers."""
        return QSize(400, 200)

    def minimumSizeHint(self) -> QSize:
        """Provide minimum size hint for layout managers."""
        return QSize(300, 150)
