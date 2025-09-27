"""
Error dialog system for PDF2Foundry GUI.

This module provides user-friendly error dialogs with actionable options,
warning prompts, and recovery mechanisms.
"""

from __future__ import annotations

import logging
from enum import Enum

from PySide6.QtCore import QObject, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QFileDialog,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QWidget,
)

from core.error_translation import to_user_error
from core.errors import BaseAppError, ErrorSeverity, ErrorType


class RecoveryAction(Enum):
    """Available recovery actions for error handling."""

    RETRY = "retry"
    SELECT_ALTERNATIVE_PATH = "select_alternative_path"
    OPEN_PERMISSIONS_HELP = "open_permissions_help"
    OPEN_SETTINGS = "open_settings"
    REPORT_ISSUE = "report_issue"
    CANCEL = "cancel"


class ErrorDialogManager(QObject):
    """
    Manager for error dialogs and user feedback.

    Provides thread-safe error dialogs with actionable recovery options
    and integrates with the existing notification system.
    """

    # Signals for recovery actions
    retryRequested = Signal()
    alternativePathRequested = Signal(str)  # new path
    settingsRequested = Signal()
    issueReportRequested = Signal(str)  # error details

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initialize the error dialog manager.

        Args:
            parent: Parent widget (typically main window)
        """
        super().__init__(parent)
        self._parent_widget = parent
        self._logger = logging.getLogger(__name__)

        # Status bar for non-blocking notifications
        self._status_bar: QStatusBar | None = None
        if parent and hasattr(parent, "statusBar"):
            self._status_bar = parent.statusBar()

    def show_error(
        self,
        app_error: BaseAppError,
        actions: list[RecoveryAction] | None = None,
        parent: QWidget | None = None,
    ) -> RecoveryAction:
        """
        Show an error dialog with actionable recovery options.

        Args:
            app_error: The error to display
            actions: Available recovery actions (auto-determined if None)
            parent: Parent widget for the dialog

        Returns:
            The recovery action chosen by the user
        """
        # Ensure we're on the main thread
        app_instance = QApplication.instance()
        if app_instance and QThread.currentThread() != app_instance.thread():
            # Schedule on main thread
            result = RecoveryAction.CANCEL
            QTimer.singleShot(0, lambda: self._show_error_main_thread(app_error, actions, parent))
            return result

        return self._show_error_main_thread(app_error, actions, parent)

    def _show_error_main_thread(
        self,
        app_error: BaseAppError,
        actions: list[RecoveryAction] | None = None,
        parent: QWidget | None = None,
    ) -> RecoveryAction:
        """Show error dialog on main thread."""
        parent = parent or self._parent_widget

        # Convert to user-friendly error
        user_error = to_user_error(app_error)

        # Auto-determine actions if not provided
        if actions is None:
            actions = self._determine_actions(app_error)

        # Create message box
        msg_box = QMessageBox(parent)
        msg_box.setWindowTitle(user_error.title)
        msg_box.setText(user_error.message)

        # Set icon based on severity
        icon_map = {
            ErrorSeverity.LOW: QMessageBox.Icon.Information,
            ErrorSeverity.MEDIUM: QMessageBox.Icon.Warning,
            ErrorSeverity.HIGH: QMessageBox.Icon.Critical,
            ErrorSeverity.CRITICAL: QMessageBox.Icon.Critical,
        }
        msg_box.setIcon(icon_map.get(app_error.severity, QMessageBox.Icon.Warning))

        # Add detailed text if available
        if user_error.details:
            msg_box.setDetailedText(user_error.details)

        # Add remediation as informative text
        if user_error.remediation:
            msg_box.setInformativeText(user_error.remediation)

        # Add action buttons
        button_map: dict[QAbstractButton, RecoveryAction] = {}
        for action in actions:
            button = self._add_action_button(msg_box, action)
            button_map[button] = action

        # Set default button (Cancel is safest)
        if RecoveryAction.CANCEL in actions:
            cancel_buttons = [btn for btn, act in button_map.items() if act == RecoveryAction.CANCEL]
            if cancel_buttons and isinstance(cancel_buttons[0], QPushButton):
                msg_box.setDefaultButton(cancel_buttons[0])

        # Show dialog
        msg_box.exec()

        # Determine which action was chosen
        clicked_button = msg_box.clickedButton()
        chosen_action: RecoveryAction = RecoveryAction.CANCEL
        if clicked_button:
            chosen_action = button_map.get(clicked_button, RecoveryAction.CANCEL)

        # Handle the action
        self._handle_recovery_action(chosen_action, app_error)

        return chosen_action

    def show_warning(self, title: str, message: str, parent: QWidget | None = None) -> bool:
        """
        Show a warning dialog.

        Args:
            title: Dialog title
            message: Warning message
            parent: Parent widget

        Returns:
            True if user clicked OK, False if cancelled
        """
        parent = parent or self._parent_widget

        msg_box = QMessageBox(parent)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        msg_box.setDefaultButton(QMessageBox.StandardButton.Cancel)

        result = msg_box.exec()
        return result == QMessageBox.StandardButton.Ok

    def confirm_destructive_action(self, context: str, parent: QWidget | None = None) -> bool:
        """
        Show a confirmation dialog for destructive actions.

        Args:
            context: Description of the destructive action
            parent: Parent widget

        Returns:
            True if user confirmed, False if cancelled
        """
        parent = parent or self._parent_widget

        msg_box = QMessageBox(parent)
        msg_box.setWindowTitle("Confirm Action")
        msg_box.setText(f"Are you sure you want to {context}?")
        msg_box.setInformativeText("This action cannot be undone.")
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        msg_box.setDefaultButton(QMessageBox.StandardButton.Cancel)

        result = msg_box.exec()
        return result == QMessageBox.StandardButton.Yes

    def show_status_notification(self, message: str, timeout: int = 3000) -> None:
        """
        Show a non-blocking status notification.

        Args:
            message: Status message
            timeout: Timeout in milliseconds (0 for permanent)
        """
        if self._status_bar:
            self._status_bar.showMessage(message, timeout)
        else:
            # Fallback to logging
            self._logger.info(f"Status: {message}")

    def _determine_actions(self, app_error: BaseAppError) -> list[RecoveryAction]:
        """Determine appropriate recovery actions based on error type and code."""
        actions = []

        # Add retry for retriable errors
        if app_error.retriable:
            actions.append(RecoveryAction.RETRY)

        # Add specific actions based on error type
        if app_error.type == ErrorType.FILE:
            if "permission" in app_error.code.value.lower():
                actions.append(RecoveryAction.OPEN_PERMISSIONS_HELP)
            if "not_found" in app_error.code.value.lower():
                actions.append(RecoveryAction.SELECT_ALTERNATIVE_PATH)

        elif app_error.type == ErrorType.VALIDATION or app_error.type == ErrorType.CONFIG:
            actions.append(RecoveryAction.OPEN_SETTINGS)

        # Always add report issue for high severity errors
        if app_error.severity in (ErrorSeverity.HIGH, ErrorSeverity.CRITICAL):
            actions.append(RecoveryAction.REPORT_ISSUE)

        # Always add cancel as the safe option
        actions.append(RecoveryAction.CANCEL)

        return actions

    def _add_action_button(self, msg_box: QMessageBox, action: RecoveryAction) -> QPushButton:
        """Add an action button to the message box."""
        button_text_map = {
            RecoveryAction.RETRY: "Retry",
            RecoveryAction.SELECT_ALTERNATIVE_PATH: "Choose Different File...",
            RecoveryAction.OPEN_PERMISSIONS_HELP: "Help with Permissions",
            RecoveryAction.OPEN_SETTINGS: "Open Settings",
            RecoveryAction.REPORT_ISSUE: "Report Issue",
            RecoveryAction.CANCEL: "Cancel",
        }

        button_role_map = {
            RecoveryAction.RETRY: QMessageBox.ButtonRole.AcceptRole,
            RecoveryAction.SELECT_ALTERNATIVE_PATH: QMessageBox.ButtonRole.ActionRole,
            RecoveryAction.OPEN_PERMISSIONS_HELP: QMessageBox.ButtonRole.HelpRole,
            RecoveryAction.OPEN_SETTINGS: QMessageBox.ButtonRole.ActionRole,
            RecoveryAction.REPORT_ISSUE: QMessageBox.ButtonRole.ActionRole,
            RecoveryAction.CANCEL: QMessageBox.ButtonRole.RejectRole,
        }

        text = button_text_map.get(action, action.value.replace("_", " ").title())
        role = button_role_map.get(action, QMessageBox.ButtonRole.ActionRole)

        return msg_box.addButton(text, role)

    def _handle_recovery_action(self, action: RecoveryAction, app_error: BaseAppError) -> None:
        """Handle the chosen recovery action."""
        try:
            if action == RecoveryAction.RETRY:
                self.retryRequested.emit()

            elif action == RecoveryAction.SELECT_ALTERNATIVE_PATH:
                # Show file dialog
                file_path, _ = QFileDialog.getOpenFileName(
                    self._parent_widget,
                    "Select Alternative File",
                    "",
                    "PDF Files (*.pdf);;All Files (*)",
                )
                if file_path:
                    self.alternativePathRequested.emit(file_path)

            elif action == RecoveryAction.OPEN_PERMISSIONS_HELP:
                # Open help documentation
                help_url = "https://github.com/your-org/pdf2foundry-gui/wiki/troubleshooting#file-permissions"
                QDesktopServices.openUrl(QUrl(help_url))

            elif action == RecoveryAction.OPEN_SETTINGS:
                self.settingsRequested.emit()

            elif action == RecoveryAction.REPORT_ISSUE:
                # Prepare error details for issue report
                error_details = self._format_error_for_report(app_error)
                self.issueReportRequested.emit(error_details)

        except Exception as e:
            self._logger.error(f"Failed to handle recovery action {action}: {e}")

    def _format_error_for_report(self, app_error: BaseAppError) -> str:
        """Format error details for issue reporting."""
        details = [
            f"Error Type: {app_error.type.value}",
            f"Error Code: {app_error.code.value}",
            f"Severity: {app_error.severity.value}",
            f"Message: {app_error.user_message}",
        ]

        if app_error.technical_message:
            details.append(f"Technical Details: {app_error.technical_message}")

        if app_error.context:
            # Filter out sensitive information
            safe_context = {
                k: v
                for k, v in app_error.context.items()
                if not any(sensitive in k.lower() for sensitive in ["password", "token", "key"])
            }
            if safe_context:
                details.append(f"Context: {safe_context}")

        return "\n".join(details)


# Convenience functions for easy access
def show_error_dialog(
    app_error: BaseAppError,
    actions: list[RecoveryAction] | None = None,
    parent: QWidget | None = None,
) -> RecoveryAction:
    """
    Show an error dialog with recovery options.

    Args:
        app_error: The error to display
        actions: Available recovery actions
        parent: Parent widget

    Returns:
        The chosen recovery action
    """
    manager = ErrorDialogManager(parent)
    return manager.show_error(app_error, actions, parent)


def show_warning_dialog(title: str, message: str, parent: QWidget | None = None) -> bool:
    """
    Show a warning dialog.

    Args:
        title: Dialog title
        message: Warning message
        parent: Parent widget

    Returns:
        True if confirmed, False if cancelled
    """
    manager = ErrorDialogManager(parent)
    return manager.show_warning(title, message, parent)


def confirm_destructive_action(context: str, parent: QWidget | None = None) -> bool:
    """
    Confirm a destructive action.

    Args:
        context: Description of the action
        parent: Parent widget

    Returns:
        True if confirmed, False if cancelled
    """
    manager = ErrorDialogManager(parent)
    return manager.confirm_destructive_action(context, parent)
