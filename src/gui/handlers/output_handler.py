"""
Output folder handling functionality for the main window.

This module contains methods for managing output directory selection,
validation, and opening folders in the system file manager.
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox

if TYPE_CHECKING:
    from gui.main_window import MainWindow


class OutputHandler:
    """Handles output folder operations for the main window."""

    def __init__(self, main_window: "MainWindow") -> None:
        """Initialize the output handler."""
        self.main_window = main_window
        self._logger = logging.getLogger(__name__)

    def on_output_dir_changed(self, path: str) -> None:
        """Handle output directory path change."""
        # Save to config for persistence
        self.main_window.config_manager.set("conversion/outputDirectory", path)

    def on_output_dir_validity_changed(self, is_valid: bool, error_message: str) -> None:
        """Handle output directory validity change."""
        # Update convert button state based on validation
        self.main_window.ui_state_handler._update_convert_button_state()

    def on_open_output_clicked(self) -> None:
        """Handle open output folder button click."""
        if not self.main_window.ui.output_dir_selector:
            self._show_output_error("Output directory selector not available")
            return

        # Get the current output path
        output_path = self.main_window.ui.output_dir_selector.path()
        if not output_path:
            self._show_output_error("No output directory selected")
            return

        # Normalize and validate the path
        try:
            path_obj = Path(output_path).resolve()
        except (OSError, ValueError) as e:
            self._show_output_error(f"Invalid output path: {e}")
            return

        # Check if path exists, create if it doesn't
        if not path_obj.exists():
            try:
                path_obj.mkdir(parents=True, exist_ok=True)
                self._logger.info(f"Created output directory: {path_obj}")
            except (OSError, PermissionError) as e:
                self._show_output_error(f"Cannot create output directory: {e}")
                return

        # Verify it's actually a directory
        if not path_obj.is_dir():
            self._show_output_error(f"Path is not a directory: {path_obj}")
            return

        # Check if we can access it
        if not os.access(path_obj, os.R_OK):
            self._show_output_error(f"Cannot access output directory: {path_obj}")
            return

        # Try to open the folder
        success = self._open_folder_with_system(path_obj)
        if not success:
            self._show_output_error(f"Failed to open folder: {path_obj}")

    def _open_folder_with_system(self, path: Path) -> bool:
        """
        Open a folder using the system's default file manager.

        Args:
            path: Path to the folder to open

        Returns:
            True if successful, False otherwise
        """
        try:
            # Try Qt's cross-platform method first
            url = QUrl.fromLocalFile(str(path))
            if QDesktopServices.openUrl(url):
                self._logger.info(f"Opened folder via QDesktopServices: {path}")
                return True

            # Fallback to platform-specific commands
            import platform

            system = platform.system().lower()

            if system == "windows":
                # Windows Explorer
                subprocess.run(["explorer", str(path)], check=True)
            elif system == "darwin":
                # macOS Finder
                subprocess.run(["open", str(path)], check=True)
            else:
                # Linux/Unix - try common file managers
                for cmd in ["xdg-open", "nautilus", "dolphin", "thunar", "pcmanfm"]:
                    try:
                        subprocess.run([cmd, str(path)], check=True)
                        self._logger.info(f"Opened folder via {cmd}: {path}")
                        return True
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        continue

                # If all else fails, try to open parent directory
                if path.parent != path:
                    return self._open_folder_with_system(path.parent)

                return False

            self._logger.info(f"Opened folder via system command: {path}")
            return True

        except (subprocess.CalledProcessError, FileNotFoundError, OSError) as e:
            self._logger.error(f"Failed to open folder {path}: {e}")
            return False

    def _show_output_error(self, message: str) -> None:
        """Show an error message related to output operations."""
        QMessageBox.warning(self.main_window, "Output Folder Error", message)
