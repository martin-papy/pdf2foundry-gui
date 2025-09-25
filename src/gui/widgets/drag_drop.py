"""
Drag-and-drop widget for PDF file selection.
"""

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent, QKeyEvent
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QSizePolicy,
    QWidget,
)

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
    pdfSelected = Signal(str)  # Emitted when a PDF is successfully selected (same as fileAccepted)
    pdfCleared = Signal()  # Emitted when the selection is cleared

    # Visual states
    STATE_NORMAL = "normal"
    STATE_HOVER = "hover"
    STATE_REJECT = "reject"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # State tracking
        self._selected_pdf_path: str = ""

        # Enable drag and drop
        self.setAcceptDrops(True)

        # Set object name for styling
        self.setObjectName("dragZone")

        # Set up initial appearance
        self._current_state = self.STATE_NORMAL
        self._setup_appearance()

        # Make focusable for accessibility
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Set accessibility properties
        self.setAccessibleName("PDF file drop zone")
        self.setAccessibleDescription("Drop a PDF file here. Only .pdf files are accepted.")
        self.setToolTip("Drop a PDF file here. Only .pdf files are accepted.")

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
            # Use dynamic properties for CSS styling
            self.setProperty("drag-hover", False)
            self.setProperty("drag-reject", False)

            # Set base styling with palette-aware colors
            self.setStyleSheet(self._get_base_stylesheet())
            self.setText("📄 Drop a PDF or use Browse\n\nSupported: .pdf files only")

        elif self._current_state == self.STATE_HOVER:
            # Set hover state properties
            self.setProperty("drag-hover", True)
            self.setProperty("drag-reject", False)

            self.setStyleSheet(self._get_hover_stylesheet())
            self.setText("📄 Drop your PDF file here")

        elif self._current_state == self.STATE_REJECT:
            # Set reject state properties
            self.setProperty("drag-hover", False)
            self.setProperty("drag-reject", True)

            self.setStyleSheet(self._get_reject_stylesheet())
            # Text will be set by the rejection handler

        # Update cursor with better feedback
        self._update_cursor()

        # Force style refresh
        self.style().unpolish(self)
        self.style().polish(self)

    def _get_base_stylesheet(self) -> str:
        """Get base stylesheet with palette-aware colors."""
        return """
            QLabel#dragZone {
                border: 2px dashed palette(mid);
                border-radius: 12px;
                background-color: rgba(128, 128, 128, 20);
                color: palette(window-text);
                font-size: 14px;
                font-weight: normal;
                padding: 24px;
                min-height: 120px;
            }
        """

    def _get_hover_stylesheet(self) -> str:
        """Get hover stylesheet with accent colors."""
        return """
            QLabel#dragZone {
                border: 2px dashed palette(highlight);
                border-radius: 12px;
                background-color: rgba(0, 120, 212, 30);
                color: palette(highlighted-text);
                font-size: 14px;
                font-weight: bold;
                padding: 24px;
                min-height: 120px;
            }
        """

    def _get_reject_stylesheet(self) -> str:
        """Get reject stylesheet with error colors."""
        return """
            QLabel#dragZone {
                border: 2px dashed #d32f2f;
                border-radius: 12px;
                background-color: rgba(211, 47, 47, 20);
                color: #d32f2f;
                font-size: 14px;
                font-weight: bold;
                padding: 24px;
                min-height: 120px;
            }
        """

    def _update_cursor(self) -> None:
        """Update cursor based on current state."""
        if self._current_state == self.STATE_HOVER:
            QApplication.setOverrideCursor(Qt.CursorShape.DragCopyCursor)
        elif self._current_state == self.STATE_REJECT:
            QApplication.setOverrideCursor(Qt.CursorShape.ForbiddenCursor)
        else:
            # Restore default cursor
            while QApplication.overrideCursor():
                QApplication.restoreOverrideCursor()

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
                # Success - update state and emit signals
                self._selected_pdf_path = str(valid_path)
                self.fileAccepted.emit(str(valid_path))
                self.pdfSelected.emit(str(valid_path))

                self._set_state(self.STATE_NORMAL)
                self.setText(f"✅ PDF Selected:\n{valid_path.name}\n\nReady to convert!")

                # Update accessibility
                self.setAccessibleDescription(f"PDF selected: {valid_path.name}")

                event.acceptProposedAction()
            else:
                # Validation failed - show error
                self._handle_rejection(error_message or "Invalid file")
                event.ignore()

        except Exception as e:
            # Unexpected error
            self._handle_rejection(f"Error processing file: {e!s}")
            event.ignore()
        finally:
            # Always restore cursor after drop
            while QApplication.overrideCursor():
                QApplication.restoreOverrideCursor()

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
        self.clearSelectedPdf()

    def set_file_selected(self, file_path: str) -> None:
        """Update the widget to show a selected file."""
        path = Path(file_path)
        self._selected_pdf_path = file_path
        self._set_state(self.STATE_NORMAL)
        self.setText(f"✅ PDF Selected:\n{path.name}\n\nReady to convert!")
        self.setAccessibleDescription(f"PDF selected: {path.name}")

    def set_error(self, error_message: str) -> None:
        """Show an error state with custom message."""
        self._handle_rejection(error_message)

    # Integration API methods

    def selectedPdfPath(self) -> str:
        """
        Get the currently selected PDF path.

        Returns:
            The absolute path to the selected PDF file, or empty string if none selected.
        """
        return self._selected_pdf_path

    def clearSelectedPdf(self) -> None:
        """Clear the current PDF selection and reset to initial state."""
        if self._selected_pdf_path:
            self._selected_pdf_path = ""
            self.pdfCleared.emit()

        self._set_state(self.STATE_NORMAL)
        self.setAccessibleDescription("Drop a PDF file here. Only .pdf files are accepted.")

        # Restore cursor if needed
        while QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()

    # Size hints for proper layout

    def sizeHint(self) -> QSize:
        """Provide size hint for layout managers."""
        return QSize(400, 200)

    def minimumSizeHint(self) -> QSize:
        """Provide minimum size hint for layout managers."""
        return QSize(300, 150)
