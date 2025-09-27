"""
Output directory selection widget for the PDF2Foundry GUI application.
"""

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFileDialog, QLabel, QLineEdit, QMessageBox, QToolButton, QWidget

from core.config_manager import ConfigManager
from gui.output.output_folder_controller import OutputFolderController, ValidationResult
from gui.widgets.directory_context_menu import DirectoryContextMenu
from gui.widgets.directory_ui_setup import DirectoryUISetup
from gui.widgets.directory_validation import DirectoryValidator


class OutputDirectorySelector(QWidget):
    """
    Widget for selecting output directory with folder browser and path validation.

    Provides a QLineEdit for displaying/editing the path, a QToolButton
    for opening a folder browser dialog, and an "Open Output Folder" button
    with integrated OutputFolderController functionality.
    """

    # Signals
    pathChanged = Signal(str)  # Emitted when the path changes
    validityChanged = Signal(bool, str)  # Emitted when validity changes (is_valid, message)
    readyForUse = Signal(bool)  # Emitted when ready state changes

    def __init__(self, parent: QWidget | None = None, config_manager: ConfigManager | None = None) -> None:
        super().__init__(parent)

        # Initialize controller
        self.controller = OutputFolderController(config_manager)

        # Internal state
        self._current_path: Path | None = None
        self._is_valid: bool = False
        self._error_message: str = ""

        # UI components (will be created by DirectoryUISetup)
        self.path_edit: QLineEdit | None = None
        self.browse_button: QToolButton | None = None
        self.open_folder_button: QToolButton | None = None
        self.validation_icon: QLabel | None = None
        self.helper_text: QLabel | None = None

        # Set up the UI
        DirectoryUISetup.setup_ui(self)
        DirectoryUISetup.setup_accessibility(self)
        self._connect_signals()

        # Set up context menu
        self.context_menu = DirectoryContextMenu(self, self.controller)

        # Initialize with controller's current path
        self._initialize_from_controller()

    def _connect_signals(self) -> None:
        """Connect widget signals to their handlers."""
        assert self.path_edit is not None, "path_edit should be initialized by DirectoryUISetup"
        assert self.browse_button is not None, "browse_button should be initialized by DirectoryUISetup"
        assert self.open_folder_button is not None, "open_folder_button should be initialized by DirectoryUISetup"

        self.browse_button.clicked.connect(self._on_browse_clicked)
        self.path_edit.textChanged.connect(self._on_text_changed)
        self.open_folder_button.clicked.connect(self._on_open_folder_clicked)

    def _initialize_from_controller(self) -> None:
        """Initialize the widget with the controller's current path."""
        current_path = self.controller.current_path()
        if current_path:
            self._apply_controller_path(current_path)

    def get_default_output_dir(self) -> Path | None:
        """Get the default output directory."""
        return DirectoryValidator.get_default_output_dir()

    def validate_path(self, path: Path | str) -> tuple[bool, str]:
        """Validate a directory path for use as output directory."""
        return DirectoryValidator.validate_path(path)

    def _on_text_changed(self, text: str) -> None:
        """Handle text changes in the path edit field."""
        if not text.strip():
            # Empty text - reset to controller's current path
            current_path = self.controller.current_path()
            self._apply_controller_path(current_path)
            return

        # Clean up the text (remove trailing spaces/newlines)
        cleaned_text = text.strip()
        if cleaned_text != text and self.path_edit:
            # Update the line edit with cleaned text
            self.path_edit.blockSignals(True)
            self.path_edit.setText(cleaned_text)
            self.path_edit.blockSignals(False)
            text = cleaned_text

        try:
            # Create path and set via controller
            path = Path(text)
            result = self.controller.set_path(path, "user")

            # Update UI based on result
            self._update_validation_state(result)

            # Update internal state
            self._current_path = result.normalized_path if result.valid or result.can_create else None

            # Emit signals
            self.validityChanged.emit(result.valid, result.message)
            self.readyForUse.emit(result.valid)

        except Exception as e:
            # Handle path creation errors
            error_msg = f"Invalid path: {e}"
            self._is_valid = False
            self._error_message = error_msg
            self._current_path = None

            if self.helper_text and self.validation_icon:
                self.helper_text.setText(error_msg)
                self.helper_text.show()
                self.validation_icon.setText("❌")
                self.validation_icon.show()

            self.validityChanged.emit(False, error_msg)
            self.readyForUse.emit(False)

    def _update_validation_ui(self, is_valid: bool, error_message: str) -> None:
        """Update the UI to reflect validation state."""
        DirectoryUISetup.update_validation_ui(self, is_valid, error_message)

    def set_path(self, path: str | Path) -> None:
        """
        Set the current path and update the UI.

        Args:
            path: The directory path to set
        """
        if isinstance(path, str):
            path = Path(path)

        # Use the controller to set the path
        result = self.controller.set_path(path, "settings")

        # Apply the result to the UI
        self._apply_controller_path(result.normalized_path)

    def path(self) -> str:
        """
        Get the current path as a string.

        Returns:
            The current directory path, or empty string if none set
        """
        if self._current_path:
            return str(self._current_path)
        assert self.path_edit is not None, "path_edit should be initialized"
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
        elif self.path_edit and self.path_edit.text().strip():
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

    def _on_open_folder_clicked(self) -> None:
        """Handle open folder button click."""
        current_path = self.controller.current_path()

        # If path doesn't exist, offer to create it
        if not current_path.exists():
            reply = QMessageBox.question(
                self,
                "Create Folder",
                f"The output folder does not exist:\n{current_path}\n\nWould you like to create it now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )

            if reply == QMessageBox.StandardButton.Yes:
                if not self.controller.ensure_exists(current_path, create_if_missing=True):
                    QMessageBox.warning(
                        self,
                        "Creation Failed",
                        f"Could not create the output folder:\n{current_path}\n\nPlease check permissions and try again.",
                    )
                    return
            else:
                return

        # Try to open in file manager
        if not self.controller.open_in_file_manager(current_path):
            QMessageBox.warning(
                self,
                "Cannot Open Folder",
                f"Could not open the output folder in your file manager:\n{current_path}\n\n"
                "The folder may be on an unmounted drive or you may not have the necessary permissions.",
            )

    def _apply_controller_path(self, path: Path) -> None:
        """Apply a path from the controller to the UI."""
        if not self.path_edit:
            return

        # Update the line edit without triggering text change events
        self.path_edit.blockSignals(True)
        self.path_edit.setText(str(path))
        self.path_edit.blockSignals(False)

        # Update internal state
        self._current_path = path

        # Validate using controller
        result = self.controller._validate_path(path)
        self._update_validation_state(result)

        # Emit signals
        self.pathChanged.emit(str(path))
        self.validityChanged.emit(result.valid, result.message)
        self.readyForUse.emit(result.valid)

    def _update_validation_state(self, result: ValidationResult) -> None:
        """Update UI validation state based on ValidationResult."""
        assert self.path_edit is not None, "path_edit should be initialized"
        assert self.validation_icon is not None, "validation_icon should be initialized"
        assert self.helper_text is not None, "helper_text should be initialized"

        self._is_valid = result.valid
        self._error_message = result.message

        # Update path edit styling
        if result.valid:
            self.path_edit.setStyleSheet("QLineEdit { border: 1px solid #28a745; background-color: #f8fff8; }")
            self.path_edit.setProperty("validation_state", "valid")
        elif result.can_create:
            self.path_edit.setStyleSheet("QLineEdit { border: 1px solid #ffc107; background-color: #fffbf0; }")
            self.path_edit.setProperty("validation_state", "warning")
        else:
            self.path_edit.setStyleSheet("QLineEdit { border: 1px solid #dc3545; background-color: #fff8f8; }")
            self.path_edit.setProperty("validation_state", "error")

        # Update validation icon and helper text
        if result.level == "error":
            self.validation_icon.setText("❌")
            self.validation_icon.setToolTip("Error")
            self.helper_text.setStyleSheet("color: #dc3545; font-size: 11px;")
        elif result.level == "warning":
            self.validation_icon.setText("⚠️")
            self.validation_icon.setToolTip("Warning")
            self.helper_text.setStyleSheet("color: #ffc107; font-size: 11px;")
        elif result.level == "info" and result.valid:
            self.validation_icon.setText("✅")
            self.validation_icon.setToolTip("Valid")
            self.helper_text.setStyleSheet("color: #28a745; font-size: 11px;")
        else:
            self.validation_icon.setText("💡")
            self.validation_icon.setToolTip("Info")
            self.helper_text.setStyleSheet("color: #17a2b8; font-size: 11px;")

        # Show/hide feedback elements
        if result.message:
            self.helper_text.setText(result.message)
            self.helper_text.show()
            self.validation_icon.show()
        else:
            self.helper_text.hide()
            self.validation_icon.hide()

        # Force style refresh
        self.path_edit.style().unpolish(self.path_edit)
        self.path_edit.style().polish(self.path_edit)

    def set_last_export_path(self, path: Path) -> None:
        """Set the last export path in the controller."""
        self.controller.set_last_export_path(path)

    def _normalize_and_set_path(self, path: Path) -> None:
        """
        Normalize a path and update the UI using the controller.

        Args:
            path: The path to normalize and set
        """
        # Use controller to set and validate the path
        result = self.controller.set_path(path, "user")

        # Update UI based on result
        if self.path_edit:
            self.path_edit.blockSignals(True)
            self.path_edit.setText(str(result.normalized_path))
            self.path_edit.blockSignals(False)

        # Update validation state
        self._update_validation_state(result)

        # Update internal state
        self._current_path = result.normalized_path if result.valid or result.can_create else None

        # Emit signals
        self.pathChanged.emit(str(result.normalized_path))
        self.validityChanged.emit(result.valid, result.message)
        self.readyForUse.emit(result.valid)
