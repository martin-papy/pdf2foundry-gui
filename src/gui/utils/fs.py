"""Cross-platform file system utilities for GUI operations.

This module provides utilities for interacting with the file system in a
cross-platform manner, particularly for opening folders in the native
file manager.
"""

import logging
import platform
import subprocess
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox, QWidget

logger = logging.getLogger(__name__)


def open_in_file_manager(path: Path, parent: QWidget | None = None) -> bool:
    """Open a folder in the OS-native file manager.

    This function attempts to open the specified path in the system's default
    file manager using Qt's QDesktopServices first, with platform-specific
    fallbacks if that fails.

    Args:
        path: The directory path to open. Must be an existing directory.
        parent: Optional parent widget for error dialogs.

    Returns:
        True if the folder was successfully opened, False otherwise.

    Note:
        If the path does not exist, this function will return False without
        attempting to open anything. Callers should handle directory creation
        separately if needed.
    """
    if not path.exists():
        logger.warning(f"Cannot open non-existent path in file manager: {path}")
        return False

    if not path.is_dir():
        logger.warning(f"Cannot open non-directory path in file manager: {path}")
        return False

    # Convert to absolute path to ensure proper handling
    abs_path = path.resolve()

    # Primary method: Qt's cross-platform approach
    try:
        url = QUrl.fromLocalFile(str(abs_path))
        if QDesktopServices.openUrl(url):
            logger.debug(f"Successfully opened {abs_path} using QDesktopServices")
            return True
        else:
            logger.warning(f"QDesktopServices.openUrl returned False for {abs_path}")
    except Exception as e:
        logger.warning(f"QDesktopServices.openUrl failed for {abs_path}: {e}")

    # Fallback to platform-specific commands
    system = platform.system().lower()

    try:
        if system == "windows":
            # Use Windows Explorer
            subprocess.run(["explorer", str(abs_path)], check=False)
            logger.debug(f"Opened {abs_path} using Windows Explorer")
            return True

        elif system == "darwin":  # macOS
            # Use macOS Finder
            subprocess.run(["open", str(abs_path)], check=False)
            logger.debug(f"Opened {abs_path} using macOS Finder")
            return True

        elif system == "linux":
            # Try xdg-open for Linux
            result = subprocess.run(["xdg-open", str(abs_path)], check=False, capture_output=True)
            if result.returncode == 0:
                logger.debug(f"Opened {abs_path} using xdg-open")
                return True
            else:
                logger.warning(f"xdg-open failed with return code {result.returncode}")

    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.error(f"Platform-specific fallback failed for {abs_path}: {e}")

    # All methods failed - show user-friendly error
    _show_file_manager_error(abs_path, parent)
    return False


def _show_file_manager_error(path: Path, parent: QWidget | None = None) -> None:
    """Show an error dialog when file manager opening fails.

    Args:
        path: The path that failed to open.
        parent: Optional parent widget for the dialog.
    """
    system = platform.system().lower()

    if system == "windows":
        suggestion = f"Try opening Windows Explorer and navigating to:\n{path}"
    elif system == "darwin":
        suggestion = f"Try opening Finder and navigating to:\n{path}"
    else:
        suggestion = f"Try opening your file manager and navigating to:\n{path}"

    message = (
        f"Could not open the folder in your file manager.\n\n"
        f"The folder may be on an unmounted drive or you may not have "
        f"the necessary permissions.\n\n"
        f"{suggestion}"
    )

    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Icon.Warning)
    msg_box.setWindowTitle("Cannot Open Folder")
    msg_box.setText("Failed to open folder in file manager")
    msg_box.setDetailedText(message)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg_box.exec()
