"""
Output directory selection widget for the PDF2Foundry GUI application.
"""

import os
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Signal
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLineEdit, QToolButton, QWidget


class OutputDirectorySelector(QWidget):
    """
    Widget for selecting output directory with folder browser and path validation.

    Provides a QLineEdit for displaying/editing the path and a QToolButton
    for opening a folder browser dialog.
    """

    # Signals
    pathChanged = Signal(str)  # Emitted when the path changes
    validityChanged = Signal(bool, str)  # Emitted when validity changes (is_valid, message)
    readyForUse = Signal(bool)  # Emitted when ready state changes

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Internal state
        self._current_path: Path | None = None
        self._is_valid: bool = False
        self._error_message: str = ""

        # Set up the UI
        self._setup_ui()
        self._setup_accessibility()
        self._connect_signals()

        # Initialize with default directory
        self._initialize_default_directory()

    def _setup_ui(self) -> None:
        """Create and arrange the UI elements."""
        # Create main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Create path line edit
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Select output folder...")

        # Create browse button with folder icon
        self.browse_button = QToolButton()
        self.browse_button.setText("📁")  # Folder emoji as fallback
        self.browse_button.setToolTip("Browse for folder")

        # Add widgets to layout with appropriate stretch
        layout.addWidget(self.path_edit, 1)  # Line edit expands
        layout.addWidget(self.browse_button, 0)  # Button stays fixed size

    def _setup_accessibility(self) -> None:
        """Set up accessibility properties and tab order."""
        # Set accessible names
        self.path_edit.setAccessibleName("Output directory path")
        self.browse_button.setAccessibleName("Browse for output directory")

        # Set accessible descriptions
        self.path_edit.setAccessibleDescription("Enter or select the output directory path")
        self.browse_button.setAccessibleDescription("Opens a folder browser dialog")

        # Set tab order
        self.setTabOrder(self.path_edit, self.browse_button)

    def _connect_signals(self) -> None:
        """Connect widget signals to their handlers."""
        self.browse_button.clicked.connect(self._on_browse_clicked)
        self.path_edit.textChanged.connect(self._on_text_changed)

    def _initialize_default_directory(self) -> None:
        """Initialize the widget with a default output directory."""
        default_dir = self.get_default_output_dir()
        if default_dir:
            self.set_path(default_dir)

    def get_default_output_dir(self) -> Path | None:
        """
        Get the default output directory.

        Returns:
            The default output directory, or None if none available
        """
        # Try Documents folder first
        documents_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)

        if documents_path:
            documents_dir = Path(documents_path)
            if documents_dir.exists() and self._is_directory_writable(documents_dir):
                return documents_dir

        # Fall back to current working directory
        try:
            cwd = Path.cwd()
            if self._is_directory_writable(cwd):
                return cwd
        except Exception:
            pass

        # Last resort: home directory
        try:
            home_dir = Path.home()
            if home_dir.exists() and self._is_directory_writable(home_dir):
                return home_dir
        except Exception:
            pass

        return None

    def _is_directory_writable(self, path: Path) -> bool:
        """
        Check if a directory is writable.

        Args:
            path: The directory path to check

        Returns:
            True if the directory is writable, False otherwise
        """
        try:
            return path.exists() and path.is_dir() and os.access(path, os.W_OK | os.X_OK)
        except Exception:
            return False

    def validate_path(self, path: Path | str) -> tuple[bool, str]:
        """
        Validate that a path exists, is a directory, and is writable.

        Args:
            path: The path to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if isinstance(path, str):
            path_str = path.strip()
            if not path_str:
                return False, "Path cannot be empty"
            path = Path(path_str)

        try:
            # Normalize the path
            normalized_path = path.expanduser().resolve()

            # Check if path exists
            if not normalized_path.exists():
                return False, f"Directory does not exist: {normalized_path}"

            # Check if it's a directory
            if not normalized_path.is_dir():
                return False, f"Path is not a directory: {normalized_path}"

            # Check if it's writable
            if not self._is_directory_writable(normalized_path):
                return False, f"Directory is not writable: {normalized_path}"

            return True, ""

        except Exception as e:
            return False, f"Invalid path: {e}"

    def _on_text_changed(self, text: str) -> None:
        """Handle text changes in the path edit field."""
        # Clean up the text (remove trailing spaces/newlines)
        cleaned_text = text.strip()
        if cleaned_text != text:
            # Update the line edit with cleaned text
            self.path_edit.blockSignals(True)
            self.path_edit.setText(cleaned_text)
            self.path_edit.blockSignals(False)
            text = cleaned_text

        # Validate the path
        is_valid, error_message = self.validate_path(text)

        # Update internal state
        self._is_valid = is_valid
        self._error_message = error_message

        # Update UI styling
        self._update_validation_ui(is_valid, error_message)

        # Update internal path if valid
        if is_valid and text:
            try:
                normalized_path = Path(text).expanduser().resolve()
                self._current_path = normalized_path
            except Exception:
                self._current_path = None
        else:
            self._current_path = None

        # Emit validity changed signal
        self.validityChanged.emit(is_valid, error_message)
        self.readyForUse.emit(is_valid)

    def _update_validation_ui(self, is_valid: bool, error_message: str) -> None:
        """
        Update the UI to reflect validation state.

        Args:
            is_valid: Whether the current path is valid
            error_message: Error message if invalid
        """
        # Set dynamic property for styling
        self.path_edit.setProperty("invalid", not is_valid)

        # Update stylesheet based on validity
        if is_valid:
            self.path_edit.setStyleSheet(
                """
                QLineEdit {
                    border: 1px solid #28a745;
                    background-color: #f8fff8;
                }
            """
            )
            # Set tooltip to show full path
            if self._current_path:
                self.path_edit.setToolTip(f"Output directory: {self._current_path}")
            else:
                self.path_edit.setToolTip("Valid output directory")
        else:
            self.path_edit.setStyleSheet(
                """
                QLineEdit {
                    border: 1px solid #dc3545;
                    background-color: #fff8f8;
                }
            """
            )
            # Set tooltip to show error message
            self.path_edit.setToolTip(error_message or "Invalid directory path")

        # Force style refresh
        self.path_edit.style().unpolish(self.path_edit)
        self.path_edit.style().polish(self.path_edit)

    def set_path(self, path: str | Path) -> None:
        """
        Set the current path and update the UI.

        Args:
            path: The directory path to set
        """
        if isinstance(path, str):
            path = Path(path)

        # Use the shared normalization logic
        self._normalize_and_set_path(path)

    def path(self) -> str:
        """
        Get the current path as a string.

        Returns:
            The current directory path, or empty string if none set
        """
        if self._current_path:
            return str(self._current_path)
        return self.path_edit.text()

    def is_valid(self) -> bool:
        """
        Check if the current path is valid.

        Returns:
            True if the path is valid, False otherwise
        """
        return self._is_valid

    def error_message(self) -> str:
        """
        Get the current error message.

        Returns:
            The error message, or empty string if no error
        """
        return self._error_message

    def is_ready_for_use(self) -> bool:
        """
        Check if the widget is ready for use (has a valid path).

        Returns:
            True if the widget has a valid path, False otherwise
        """
        return self._is_valid

    def _on_browse_clicked(self) -> None:
        """Handle browse button click to open folder dialog."""
        # Determine starting directory
        start_dir = ""
        if self._current_path and self._current_path.exists():
            start_dir = str(self._current_path)
        elif self.path_edit.text().strip():
            # Try to use the text in the line edit
            try:
                potential_path = Path(self.path_edit.text().strip()).expanduser()
                if potential_path.exists() and potential_path.is_dir():
                    start_dir = str(potential_path)
            except Exception:
                pass

        # If no valid start directory, use default
        if not start_dir:
            default_dir = self.get_default_output_dir()
            start_dir = str(default_dir) if default_dir else str(Path.home())

        # Open folder dialog
        selected_dir = QFileDialog.getExistingDirectory(
            self, "Select Output Folder", start_dir, QFileDialog.Option.ShowDirsOnly
        )

        # Handle cancellation (empty string)
        if not selected_dir:
            return

        # Normalize and set the selected path
        self._normalize_and_set_path(Path(selected_dir))

    def _normalize_and_set_path(self, path: Path) -> None:
        """
        Normalize a path and update the UI.

        Args:
            path: The path to normalize and set
        """
        try:
            # Normalize the path: expanduser, resolve, absolute
            normalized_path = path.expanduser().resolve().absolute()

            # Handle Windows drive/UNC paths if needed
            self._current_path = normalized_path

            # Display using native separators
            display_path = str(normalized_path)
            self.path_edit.setText(display_path)

            # Update tooltip with full path
            self.path_edit.setToolTip(f"Output directory: {display_path}")

            # Emit pathChanged signal
            self.pathChanged.emit(str(normalized_path))

        except Exception as e:
            # Handle normalization errors
            self._current_path = None
            self.path_edit.setText(str(path))
            self.path_edit.setToolTip(f"Invalid path: {e}")
            self.pathChanged.emit(str(path))
