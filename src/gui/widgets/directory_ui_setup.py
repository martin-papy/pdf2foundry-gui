"""
UI setup and styling utilities for the output directory selector widget.
"""

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QToolButton, QVBoxLayout

if TYPE_CHECKING:
    from gui.widgets.directory_selector import OutputDirectorySelector


class DirectoryUISetup:
    """Handles UI setup and styling for the directory selector widget."""

    @staticmethod
    def setup_ui(widget: "OutputDirectorySelector") -> None:
        """Create and arrange the UI elements."""
        # Create main vertical layout for the entire widget
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        # Create horizontal layout for path input and buttons
        input_layout = QHBoxLayout()
        input_layout.setSpacing(6)

        # Create path line edit
        widget.path_edit = QLineEdit()
        widget.path_edit.setPlaceholderText("Select output folder...")

        # Create browse button with folder icon
        widget.browse_button = QToolButton()
        widget.browse_button.setText("📁")  # Folder emoji as fallback
        widget.browse_button.setToolTip("Browse for folder")

        # Create open folder button
        widget.open_folder_button = QToolButton()
        widget.open_folder_button.setText("📂")  # Open folder emoji
        widget.open_folder_button.setToolTip("Open Output Folder in File Manager")

        # Add widgets to input layout
        input_layout.addWidget(widget.path_edit, 1)  # Line edit expands
        input_layout.addWidget(widget.browse_button, 0)  # Browse button stays fixed
        input_layout.addWidget(widget.open_folder_button, 0)  # Open button stays fixed

        # Create validation feedback layout
        feedback_layout = QHBoxLayout()
        feedback_layout.setSpacing(4)

        # Create validation icon
        widget.validation_icon = QLabel()
        widget.validation_icon.setFixedSize(16, 16)
        widget.validation_icon.hide()  # Initially hidden

        # Create helper text label
        widget.helper_text = QLabel()
        widget.helper_text.setWordWrap(True)
        widget.helper_text.hide()  # Initially hidden

        # Add validation widgets to feedback layout
        feedback_layout.addWidget(widget.validation_icon, 0)
        feedback_layout.addWidget(widget.helper_text, 1)

        # Add layouts to main layout
        main_layout.addLayout(input_layout)
        main_layout.addLayout(feedback_layout)

    @staticmethod
    def setup_accessibility(widget: "OutputDirectorySelector") -> None:
        """Set up accessibility properties for the widget components."""
        if hasattr(widget, "path_edit") and widget.path_edit:
            widget.path_edit.setAccessibleName("Output directory path")
            widget.path_edit.setAccessibleDescription("Enter or select the directory where converted files will be saved")

        if hasattr(widget, "browse_button") and widget.browse_button:
            widget.browse_button.setAccessibleName("Browse for output directory")
            widget.browse_button.setAccessibleDescription("Opens a folder browser dialog to select the output directory")

        if hasattr(widget, "open_folder_button") and widget.open_folder_button:
            widget.open_folder_button.setAccessibleName("Open output folder")
            widget.open_folder_button.setAccessibleDescription("Opens the current output directory in the file manager")

    @staticmethod
    def update_validation_ui(widget: "OutputDirectorySelector", is_valid: bool, error_message: str) -> None:
        """Update the validation UI based on validation state."""
        if not hasattr(widget, "validation_icon") or not hasattr(widget, "helper_text"):
            return

        # Assert that UI components exist after setup
        assert widget.validation_icon is not None
        assert widget.helper_text is not None

        if is_valid:
            # Valid state - show success icon and message
            widget.validation_icon.setText("✅")
            widget.validation_icon.setToolTip("Valid directory")
            widget.validation_icon.show()

            if error_message:  # Success message
                widget.helper_text.setText(error_message)
                widget.helper_text.setStyleSheet("color: green; font-size: 11px;")
                widget.helper_text.show()
            else:
                widget.helper_text.hide()

            # Update line edit styling for valid state
            if hasattr(widget, "path_edit") and widget.path_edit:
                widget.path_edit.setStyleSheet("QLineEdit { border: 1px solid green; }")
        else:
            # Invalid state - show error icon and message
            if error_message:
                widget.validation_icon.setText("❌")
                widget.validation_icon.setToolTip("Invalid directory")
                widget.validation_icon.show()

                widget.helper_text.setText(error_message)
                widget.helper_text.setStyleSheet("color: red; font-size: 11px;")
                widget.helper_text.show()

                # Update line edit styling for invalid state
                if hasattr(widget, "path_edit") and widget.path_edit:
                    widget.path_edit.setStyleSheet("QLineEdit { border: 1px solid red; }")
            else:
                # No error message - hide validation UI
                widget.validation_icon.hide()
                widget.helper_text.hide()

                # Reset line edit styling
                if hasattr(widget, "path_edit") and widget.path_edit:
                    widget.path_edit.setStyleSheet("")
