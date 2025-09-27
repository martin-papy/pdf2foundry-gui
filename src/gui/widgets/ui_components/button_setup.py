"""
Button setup utilities for the main window UI.

This module contains methods for setting up buttons and controls
in the main window interface.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QToolButton, QVBoxLayout

if TYPE_CHECKING:
    from gui.widgets.main_window_ui import MainWindowUI


class ButtonSetup:
    """Handles button setup for the main window UI."""

    def __init__(self, ui_instance: "MainWindowUI") -> None:
        """Initialize with reference to the UI instance."""
        self.ui = ui_instance

    def setup_button_controls_area(self, main_layout: QVBoxLayout) -> None:
        """Set up the button controls area with convert, cancel, and open output buttons."""
        # Create browse button first
        self.ui.browse_button = QPushButton("Browse…")
        self.ui.browse_button.setObjectName("browseButton")
        self.ui.browse_button.setMinimumHeight(40)
        self.ui.browse_button.setAccessibleName("Browse for PDF")
        self.ui.browse_button.setAccessibleDescription("Opens a file dialog filtered to PDF files")
        self.ui.browse_button.setToolTip("Choose a PDF file (Ctrl+O)")
        main_layout.addWidget(self.ui.browse_button)

        # Create horizontal layout for action buttons
        action_buttons_layout = QHBoxLayout()
        action_buttons_layout.setSpacing(12)
        action_buttons_layout.setContentsMargins(0, 0, 0, 0)

        # Convert button (primary action)
        self.ui.convert_button = QPushButton("Convert")
        self.ui.convert_button.setObjectName("convertButton")
        self.ui.convert_button.setMinimumHeight(50)
        self.ui.convert_button.setMinimumWidth(120)
        self.ui.convert_button.setAccessibleName("Convert PDF to Foundry VTT module")
        self.ui.convert_button.setAccessibleDescription(
            "Starts the conversion process to transform the selected PDF into a Foundry VTT module"
        )
        self.ui.convert_button.setToolTip("Convert the selected PDF to a Foundry VTT module (Ctrl+Enter)")
        self.ui.convert_button.setDefault(True)
        self.ui.convert_button.setAutoDefault(True)
        self.ui.convert_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        action_buttons_layout.addWidget(self.ui.convert_button)

        # Cancel/Stop button (secondary action, initially hidden)
        self.ui.cancel_button = QPushButton("Stop")
        self.ui.cancel_button.setObjectName("cancelButton")
        self.ui.cancel_button.setMinimumHeight(50)
        self.ui.cancel_button.setMinimumWidth(120)
        self.ui.cancel_button.setAccessibleName("Stop or cancel conversion")
        self.ui.cancel_button.setAccessibleDescription(
            "Stops the current conversion and attempts to cancel any ongoing processing"
        )
        self.ui.cancel_button.setToolTip("Stop the current conversion (Esc)")
        self.ui.cancel_button.setVisible(False)  # Hidden initially
        self.ui.cancel_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        action_buttons_layout.addWidget(self.ui.cancel_button)

        # Open output folder button (utility action)
        self.ui.open_output_button = QToolButton()
        self.ui.open_output_button.setObjectName("openOutputButton")
        self.ui.open_output_button.setText("📁")  # Folder emoji as icon
        self.ui.open_output_button.setMinimumHeight(50)
        self.ui.open_output_button.setMinimumWidth(60)
        self.ui.open_output_button.setAccessibleName("Open output folder")
        self.ui.open_output_button.setAccessibleDescription("Opens the output directory in your system's file manager")
        self.ui.open_output_button.setToolTip("Open the output folder in file manager (Ctrl+Shift+O)")
        self.ui.open_output_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        action_buttons_layout.addWidget(self.ui.open_output_button)

        # Add stretch to push buttons to the left
        action_buttons_layout.addStretch()

        # Add the button layout to main layout
        main_layout.addLayout(action_buttons_layout)
