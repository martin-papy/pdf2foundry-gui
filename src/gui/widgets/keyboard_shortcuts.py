"""
Keyboard shortcuts setup for the main window.

This module handles all keyboard shortcut configuration,
separating shortcut management from main UI layout.
"""

from typing import Any

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMainWindow


class KeyboardShortcutsManager:
    """
    Manages keyboard shortcuts for the main window.

    Provides centralized shortcut configuration and management.
    """

    def __init__(self, main_window: QMainWindow) -> None:
        """
        Initialize the shortcuts manager.

        Args:
            main_window: The main window to add shortcuts to
        """
        self.main_window = main_window

    def setup_shortcuts(
        self,
        browse_button: Any = None,
        help_button: Any = None,
        settings_button: Any = None,
        output_dir_selector: Any = None,
        log_toggle_button: Any = None,
        convert_button: Any = None,
        cancel_button: Any = None,
        open_output_button: Any = None,
    ) -> None:
        """
        Set up all keyboard shortcuts.

        Args:
            browse_button: Browse button widget
            help_button: Help button widget
            settings_button: Settings button widget
            output_dir_selector: Output directory selector widget
            log_toggle_button: Log toggle button widget
            convert_button: Convert button widget
            cancel_button: Cancel button widget
            open_output_button: Open output button widget
        """
        # Browse shortcut
        browse_action = QAction(self.main_window)
        browse_action.setShortcut(QKeySequence("Ctrl+O"))
        browse_action.triggered.connect(lambda: browse_button.clicked.emit() if browse_button else None)
        self.main_window.addAction(browse_action)

        # Help shortcut
        help_action = QAction(self.main_window)
        help_action.setShortcut(QKeySequence("F1"))
        help_action.triggered.connect(lambda: help_button.clicked.emit() if help_button else None)
        self.main_window.addAction(help_action)

        # Settings shortcut
        settings_action = QAction(self.main_window)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(lambda: settings_button.clicked.emit() if settings_button else None)
        self.main_window.addAction(settings_action)

        # Output directory browse shortcut
        output_dir_action = QAction(self.main_window)
        output_dir_action.setShortcut(QKeySequence("Alt+O"))
        output_dir_action.triggered.connect(
            lambda: output_dir_selector.browse_button.clicked.emit() if output_dir_selector else None
        )
        self.main_window.addAction(output_dir_action)

        # Log panel toggle shortcut
        log_toggle_action = QAction(self.main_window)
        log_toggle_action.setShortcut(QKeySequence("Alt+L"))
        log_toggle_action.triggered.connect(lambda: log_toggle_button.toggle() if log_toggle_button else None)
        self.main_window.addAction(log_toggle_action)

        # Convert shortcut (Ctrl+Enter)
        convert_action = QAction(self.main_window)
        convert_action.setShortcut(QKeySequence("Ctrl+Return"))
        convert_action.triggered.connect(
            lambda: convert_button.clicked.emit() if convert_button and convert_button.isEnabled() else None
        )
        self.main_window.addAction(convert_action)

        # Cancel shortcut (Escape)
        cancel_action = QAction(self.main_window)
        cancel_action.setShortcut(QKeySequence("Escape"))
        cancel_action.triggered.connect(
            lambda: (
                cancel_button.clicked.emit()
                if cancel_button and cancel_button.isVisible() and cancel_button.isEnabled()
                else None
            )
        )
        self.main_window.addAction(cancel_action)

        # Open output folder shortcut (Ctrl+Shift+O)
        open_output_action = QAction(self.main_window)
        open_output_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
        open_output_action.triggered.connect(
            lambda: open_output_button.clicked.emit() if open_output_button and open_output_button.isEnabled() else None
        )
        self.main_window.addAction(open_output_action)
