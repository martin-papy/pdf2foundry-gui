"""
Settings management utilities for the main window UI.

This module contains methods for loading and saving UI settings
and managing UI state persistence.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QSettings, QStandardPaths
from PySide6.QtWidgets import QSplitter

if TYPE_CHECKING:
    from gui.widgets.main_window_ui import MainWindowUI


class UISettingsManager:
    """Handles UI settings management."""

    def __init__(self, ui_instance: "MainWindowUI") -> None:
        """Initialize with reference to the UI instance."""
        self.ui = ui_instance
        self._logger = logging.getLogger(__name__)

    def load_ui_settings(self) -> None:
        """Load UI settings from QSettings."""
        settings = QSettings()

        # Load window geometry and state
        if hasattr(self.ui.main_window, "restoreGeometry"):
            geometry = settings.value("ui/geometry")
            if geometry and isinstance(geometry, bytes | bytearray):
                self.ui.main_window.restoreGeometry(geometry)

        if hasattr(self.ui.main_window, "restoreState"):
            state = settings.value("ui/windowState")
            if state and isinstance(state, bytes | bytearray):
                self.ui.main_window.restoreState(state)

        # Load splitter state
        if hasattr(self.ui, "main_splitter") and isinstance(self.ui.main_splitter, QSplitter):
            splitter_state = settings.value("ui/splitterState")
            if splitter_state and isinstance(splitter_state, bytes | bytearray):
                self.ui.main_splitter.restoreState(splitter_state)
            else:
                # Set default splitter sizes (70% main content, 30% log panel)
                total_height = 600  # Default height
                self.ui.main_splitter.setSizes([int(total_height * 0.7), int(total_height * 0.3)])

        # Load log panel visibility
        if hasattr(self.ui, "log_console") and self.ui.log_console:
            log_visible = settings.value("ui/logPanelVisible", True, type=bool)
            if hasattr(self.ui.log_console, "setVisible") and isinstance(log_visible, bool):
                self.ui.log_console.setVisible(log_visible)

    def save_ui_settings(self) -> None:
        """Save UI settings to QSettings."""
        settings = QSettings()

        # Save window geometry and state
        if hasattr(self.ui.main_window, "saveGeometry"):
            settings.setValue("ui/geometry", self.ui.main_window.saveGeometry())

        if hasattr(self.ui.main_window, "saveState"):
            settings.setValue("ui/windowState", self.ui.main_window.saveState())

        # Save splitter state
        if hasattr(self.ui, "main_splitter") and isinstance(self.ui.main_splitter, QSplitter):
            settings.setValue("ui/splitterState", self.ui.main_splitter.saveState())

        # Save log panel visibility
        if hasattr(self.ui, "log_console") and self.ui.log_console and hasattr(self.ui.log_console, "isVisible"):
            settings.setValue("ui/logPanelVisible", self.ui.log_console.isVisible())

        self._logger.debug("UI settings saved")

    def get_default_output_directory(self) -> Path:
        """
        Get the default output directory.

        Returns:
            Path to the default output directory
        """
        # Try to get Documents folder
        documents_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        if documents_path:
            return Path(documents_path) / "FoundryVTT_Modules"

        # Fallback to current working directory
        return Path.cwd() / "output"

    def on_log_toggle_splitter(self, expanded: bool) -> None:
        """
        Handle log panel toggle in splitter.

        Args:
            expanded: Whether the log panel is expanded
        """
        if not hasattr(self.ui, "main_splitter") or not self.ui.main_splitter:
            return

        if expanded:
            # Restore previous sizes or use defaults
            settings = QSettings()
            splitter_state = settings.value("ui/splitterState")
            if splitter_state and isinstance(splitter_state, bytes | bytearray):
                self.ui.main_splitter.restoreState(splitter_state)
            else:
                # Default: 70% main content, 30% log panel
                total_height = self.ui.main_splitter.height()
                if total_height > 0:
                    self.ui.main_splitter.setSizes([int(total_height * 0.7), int(total_height * 0.3)])
        else:
            # Collapse log panel
            sizes = self.ui.main_splitter.sizes()
            if len(sizes) >= 2:
                # Give all space to the main content
                total = sum(sizes)
                self.ui.main_splitter.setSizes([total, 0])
