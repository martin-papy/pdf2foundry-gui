"""
Module configuration setup utilities for the main window UI.

This module contains methods for setting up module configuration
inputs in the main window interface.
"""

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QVBoxLayout

if TYPE_CHECKING:
    from gui.widgets.main_window_ui import MainWindowUI


class ModuleConfigSetup:
    """Handles module configuration setup for the main window UI."""

    def __init__(self, ui_instance: "MainWindowUI") -> None:
        """Initialize with reference to the UI instance."""
        self.ui = ui_instance

    def setup_module_config_section(self, controls_layout: QVBoxLayout) -> None:
        """Set up the module configuration input section."""
        # Module configuration inputs
        module_layout = QVBoxLayout()
        module_layout.setSpacing(8)

        # Module ID input
        id_layout = QHBoxLayout()
        id_label = QLabel("Module ID:")
        id_label.setMinimumWidth(100)
        id_label.setAccessibleName("Module ID label")
        self.ui.module_id_input = QLineEdit()
        self.ui.module_id_input.setObjectName("moduleIdInput")
        self.ui.module_id_input.setPlaceholderText("e.g., my-adventure-module")
        self.ui.module_id_input.setAccessibleName("Module ID")
        self.ui.module_id_input.setAccessibleDescription(
            "Enter a unique identifier for your module using lowercase letters, numbers, and hyphens"
        )
        self.ui.module_id_input.setToolTip(
            "Unique module identifier (lowercase, hyphens allowed)\nExample: my-adventure-module"
        )
        id_layout.addWidget(id_label)
        id_layout.addWidget(self.ui.module_id_input)
        module_layout.addLayout(id_layout)

        # Module title input
        title_layout = QHBoxLayout()
        title_label = QLabel("Module Title:")
        title_label.setMinimumWidth(100)
        title_label.setAccessibleName("Module title label")
        self.ui.module_title_input = QLineEdit()
        self.ui.module_title_input.setObjectName("moduleTitleInput")
        self.ui.module_title_input.setPlaceholderText("e.g., My Adventure Module")
        self.ui.module_title_input.setAccessibleName("Module title")
        self.ui.module_title_input.setAccessibleDescription("Enter a human-readable title for your module")
        self.ui.module_title_input.setToolTip("Display name for your module\nExample: My Adventure Module")
        title_layout.addWidget(title_label)
        title_layout.addWidget(self.ui.module_title_input)
        module_layout.addLayout(title_layout)

        controls_layout.addLayout(module_layout)
