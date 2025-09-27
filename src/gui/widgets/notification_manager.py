"""
Notification management for the PDF2Foundry GUI.

This module provides a unified notification system that can display
messages via QMessageBox or system tray notifications depending on
the application state.
"""

import contextlib
import logging
from pathlib import Path
from time import monotonic
from typing import Any

from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon, QWidget


class NotificationManager(QObject):
    """
    Manages notifications for the application.

    Provides a unified interface for showing notifications either as
    message boxes (when window is active) or system tray notifications
    (when window is minimized or in background).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initialize the notification manager.

        Args:
            parent: Parent widget (typically main window)
        """
        super().__init__(parent)
        self._parent_widget = parent
        self._logger = logging.getLogger(__name__)

        # System tray icon (singleton)
        self._system_tray: QSystemTrayIcon | None = None
        self._tray_available = False

        # Notification debouncing
        self._notification_cache: dict[tuple[Any, ...], float] = {}
        self._debounce_ttl = 3.0  # 3 seconds

        # Conversion-specific deduplication
        self._notified_conversions: dict[str, str] = {}  # conversion_id -> outcome

        # Test mode detection
        self._test_mode = self._detect_test_mode()

        # Initialize system tray if available and not in test mode
        if not self._test_mode:
            self._init_system_tray()

    def _init_system_tray(self) -> None:
        """Initialize system tray icon if available."""
        if QSystemTrayIcon.isSystemTrayAvailable():
            self._system_tray = QSystemTrayIcon(self)

            # Set application icon (use default for now)
            app_instance = QApplication.instance()
            app_icon = app_instance.windowIcon() if app_instance and hasattr(app_instance, "windowIcon") else QIcon()
            if not app_icon.isNull():
                self._system_tray.setIcon(app_icon)

            self._system_tray.setToolTip("PDF2Foundry GUI")
            self._system_tray.show()
            self._tray_available = True

            self._logger.debug("System tray initialized")
        else:
            self._logger.debug("System tray not available")

    def _detect_test_mode(self) -> bool:
        """Detect if we're running in test mode."""
        import sys

        # Check for pytest in the command line or imported modules
        return (
            "pytest" in sys.modules
            or "unittest" in sys.modules
            or any("test" in arg.lower() for arg in sys.argv)
            or hasattr(sys, "_called_from_test")
        )

    def notify(
        self, status: str, title: str, message: str, output_path: str | None = None, job_id: str | None = None
    ) -> None:
        """
        Show a notification to the user.

        Args:
            status: Notification status ('success', 'error', 'warning', 'info')
            title: Notification title
            message: Notification message
            output_path: Optional path to output folder for "Open Folder" action
            job_id: Optional job identifier for debouncing
        """
        # In test mode, just log the notification instead of showing UI
        if self._test_mode:
            self._logger.info(
                f"TEST NOTIFICATION [{status}] {title}: {message} " f"(output_path={output_path}, job_id={job_id})"
            )
            return

        # Check for conversion-specific deduplication
        if job_id and status in ["success", "error", "warning"]:
            if job_id in self._notified_conversions:
                previous_outcome = self._notified_conversions[job_id]
                self._logger.debug(f"Conversion {job_id} already notified with outcome: {previous_outcome}")
                return
            # Record this conversion outcome
            self._notified_conversions[job_id] = status

        # Create debounce key
        debounce_key = (job_id, status, title, message, output_path)

        # Check if this notification was recently shown
        if self._should_debounce(debounce_key):
            self._logger.debug(f"Debouncing notification: {title}")
            return

        # Record this notification
        self._notification_cache[debounce_key] = monotonic()

        # Determine notification method
        if self._should_use_system_tray():
            self._show_tray_notification(status, title, message, output_path)
        else:
            self._show_message_box(status, title, message, output_path)

    def _should_debounce(self, key: tuple[Any, ...]) -> bool:
        """Check if notification should be debounced."""
        if key not in self._notification_cache:
            return False

        # Check if TTL has expired
        age = monotonic() - self._notification_cache[key]
        if age > self._debounce_ttl:
            # Remove expired entry
            del self._notification_cache[key]
            return False

        return True

    def _should_use_system_tray(self) -> bool:
        """Determine if system tray notification should be used."""
        if not self._tray_available or not self._system_tray:
            return False

        # Use tray if parent window is minimized or not active
        if self._parent_widget:
            return self._parent_widget.isMinimized() or not self._parent_widget.isActiveWindow()

        return False

    def _show_message_box(self, status: str, title: str, message: str, output_path: str | None = None) -> None:
        """Show notification as a message box."""
        if not self._parent_widget:
            self._logger.warning("No parent widget for message box")
            return

        msg_box = QMessageBox(self._parent_widget)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)

        # Set appropriate icon based on status
        icon_map = {
            "success": QMessageBox.Icon.Information,
            "error": QMessageBox.Icon.Critical,
            "warning": QMessageBox.Icon.Warning,
            "info": QMessageBox.Icon.Information,
        }
        msg_box.setIcon(icon_map.get(status, QMessageBox.Icon.Information))

        # Add standard OK button
        ok_button = msg_box.addButton(QMessageBox.StandardButton.Ok)
        msg_box.setDefaultButton(ok_button)

        # Add "Open Folder" button if output path is provided
        open_folder_button = None
        if output_path and Path(output_path).exists():
            open_folder_button = msg_box.addButton(self.tr("Open Folder"), QMessageBox.ButtonRole.ActionRole)

        # Show the message box
        msg_box.exec()

        # Handle "Open Folder" button click
        if open_folder_button and msg_box.clickedButton() == open_folder_button and output_path:
            self._open_output_folder(output_path)

    def _show_tray_notification(self, status: str, title: str, message: str, output_path: str | None = None) -> None:
        """Show notification via system tray."""
        if not self._system_tray:
            # Fallback to message box
            self._show_message_box(status, title, message, output_path)
            return

        # Map status to tray icon
        icon_map = {
            "success": QSystemTrayIcon.MessageIcon.Information,
            "error": QSystemTrayIcon.MessageIcon.Critical,
            "warning": QSystemTrayIcon.MessageIcon.Warning,
            "info": QSystemTrayIcon.MessageIcon.Information,
        }

        tray_icon = icon_map.get(status, QSystemTrayIcon.MessageIcon.Information)

        # Add action hint for output path
        tray_message = message
        if output_path and Path(output_path).exists():
            tray_message += f"\n{self.tr('Click to open folder')}"

            # Connect message clicked signal (disconnect previous connections)
            with contextlib.suppress(TypeError):
                self._system_tray.messageClicked.disconnect()

            self._system_tray.messageClicked.connect(lambda: self._open_output_folder(output_path))

        # Show tray notification
        self._system_tray.showMessage(title, tray_message, tray_icon, 5000)  # 5 second timeout

    def _open_output_folder(self, output_path: str) -> None:
        """Open output folder using the main window's method or fallback."""
        try:
            # Try to use main window's method if available
            if (
                self._parent_widget
                and hasattr(self._parent_widget, "on_open_output_clicked")
                and callable(self._parent_widget.on_open_output_clicked)
            ):
                # Set the path in the output selector if needed
                if (
                    hasattr(self._parent_widget, "ui")
                    and self._parent_widget.ui
                    and hasattr(self._parent_widget.ui, "output_dir_selector")
                    and self._parent_widget.ui.output_dir_selector
                ):
                    current_path = self._parent_widget.ui.output_dir_selector.path()
                    if not current_path or current_path != output_path:
                        self._parent_widget.ui.output_dir_selector.set_path(output_path)

                # Call the main window's method
                self._parent_widget.on_open_output_clicked()
            else:
                # Fallback to direct opening
                url = QUrl.fromLocalFile(output_path)
                QDesktopServices.openUrl(url)

        except Exception as e:
            self._logger.error(f"Failed to open output folder: {e}")

    def cleanup(self) -> None:
        """Clean up resources."""
        if self._system_tray:
            self._system_tray.hide()
            self._system_tray = None

        # Clear notification cache
        self._notification_cache.clear()
        self._notified_conversions.clear()

    def tr(self, sourceText: str, disambiguation: str | None = None, n: int = -1) -> str:
        """Translate text (placeholder for future localization)."""
        return sourceText  # TODO: Implement proper translation when i18n is added
