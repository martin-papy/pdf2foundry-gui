"""
Window properties and configuration for the main window.

This module handles window setup, icon configuration, and
platform-specific window behavior.
"""

import os
import platform
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QMainWindow


class WindowPropertiesManager:
    """
    Manages window properties and configuration.

    Handles window title, icon, size, and platform-specific settings.
    """

    def __init__(self, main_window: QMainWindow) -> None:
        """
        Initialize the window properties manager.

        Args:
            main_window: The main window to configure
        """
        self.main_window = main_window
        self.custom_title_bar_enabled = False

    def setup_window_properties(self) -> None:
        """Set up basic window properties."""
        self.main_window.setWindowTitle("PDF2Foundry GUI")
        self.main_window.setMinimumSize(800, 600)
        self.main_window.resize(800, 600)

        # Set window icon (create a simple icon if none exists)
        self._setup_window_icon()

        # Check for custom frameless mode (feature flag)
        self._check_custom_frameless_mode()

    def _setup_window_icon(self) -> None:
        """Set up the window icon."""
        # Try to load icon from resources first
        icon_path = Path("resources/icons/app_icon.png")
        if icon_path.exists():
            icon = QIcon(str(icon_path))
            self.main_window.setWindowIcon(icon)
        else:
            # Create a simple fallback icon using text
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.GlobalColor.transparent)
            # For now, just use the default system icon
            # In a real application, you would create a proper icon here
            pass

    def _check_custom_frameless_mode(self) -> None:
        """Check if custom frameless mode should be enabled."""
        # Check for environment variable or config setting
        enable_frameless = os.environ.get("PDF2FOUNDRY_CUSTOM_TITLEBAR", "false").lower() == "true"

        # Avoid frameless on macOS by default due to complexity with traffic lights
        if platform.system() == "Darwin" and not os.environ.get("PDF2FOUNDRY_FORCE_FRAMELESS"):
            enable_frameless = False

        if enable_frameless:
            self.custom_title_bar_enabled = True
            self.main_window.setWindowFlags(self.main_window.windowFlags() | Qt.WindowType.FramelessWindowHint)
            # Note: In a full implementation, you would add custom title bar widgets here
