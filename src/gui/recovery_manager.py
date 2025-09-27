"""
Recovery and retry flow management for PDF2Foundry GUI.

This module provides coordinated recovery actions for failed conversions,
including retry logic with exponential backoff and thread-safe integration
with the conversion system.
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal, Slot
from PySide6.QtWidgets import QWidget

from core.conversion_config import ConversionConfig
from core.errors import BaseAppError
from gui.dialogs.error_dialogs import ErrorDialogManager, RecoveryAction


class RecoveryManager(QObject):
    """
    Manages recovery flows for failed conversion operations.

    Coordinates with ErrorDialogManager for user interaction and
    ConversionController for thread management, providing retry
    logic with exponential backoff and safe thread coordination.
    """

    # Signals for recovery coordination
    recoveryRequested = Signal(object, dict)  # app_error, context
    performRetryRequested = Signal(int)  # delay_ms
    cancelRequested = Signal()
    alternativePathSelected = Signal(str)  # new_path
    settingsRequested = Signal()
    issueReportRequested = Signal(str)  # error_details

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._logger = logging.getLogger(__name__)

        # Recovery state
        self._attempt_count = 0
        self._max_attempts = 3
        self._base_backoff_ms = 1000  # 1 second
        self._max_backoff_ms = 30000  # 30 seconds
        self._in_recovery = False
        self._current_job_id: str | None = None
        self._current_config: ConversionConfig | None = None

        # Retry timer
        self._retry_timer = QTimer()
        self._retry_timer.setSingleShot(True)
        self._retry_timer.timeout.connect(self._execute_retry)

        # Error dialog manager
        widget_parent = parent if isinstance(parent, QWidget) else None
        self._error_dialog_manager = ErrorDialogManager(widget_parent)
        self._connect_error_dialog_signals()

    def _connect_error_dialog_signals(self) -> None:
        """Connect error dialog manager signals."""
        self._error_dialog_manager.retryRequested.connect(self._on_retry_requested)
        self._error_dialog_manager.alternativePathRequested.connect(self._on_alternative_path_requested)
        self._error_dialog_manager.settingsRequested.connect(self._on_settings_requested)
        self._error_dialog_manager.issueReportRequested.connect(self._on_issue_report_requested)

    def start(self, job_id: str, config: ConversionConfig) -> None:
        """
        Start recovery management for a new job.

        Args:
            job_id: Unique identifier for the job
            config: Conversion configuration
        """
        self._current_job_id = job_id
        self._current_config = config
        self._attempt_count = 0
        self._in_recovery = False
        self._retry_timer.stop()

        self._logger.debug(f"Started recovery management for job {job_id}")

    @Slot(str, str)
    def on_conversion_error(self, error_type: str, traceback_str: str) -> None:
        """
        Handle conversion error and initiate recovery flow.

        Args:
            error_type: Type of error that occurred
            traceback_str: Full traceback string
        """
        if self._in_recovery:
            self._logger.debug("Already in recovery, ignoring duplicate error")
            return

        self._in_recovery = True
        self._attempt_count += 1

        # Create error context
        context = {
            "job_id": self._current_job_id,
            "attempt": self._attempt_count,
            "max_attempts": self._max_attempts,
            "error_type": error_type,
            "traceback": traceback_str,
        }

        # Log the error
        self._logger.error(
            f"Conversion error on attempt {self._attempt_count}/{self._max_attempts}: {error_type}",
            extra={"job_id": self._current_job_id},
        )

        # Create BaseAppError from the error information
        from core.errors import map_exception

        try:
            # Try to recreate the original exception for better error mapping
            app_error = map_exception(Exception(error_type), context)
        except Exception:
            # Fallback to generic system error
            from core.errors import ErrorCode, SystemError

            app_error = SystemError(
                code=ErrorCode.BACKEND_FAILURE,
                user_message=f"Conversion failed: {error_type}",
                technical_message=traceback_str,
                context=context,
            )

        # Show error dialog and get recovery action
        self._show_recovery_dialog(app_error, context)

    def _show_recovery_dialog(self, app_error: BaseAppError, context: dict[str, Any]) -> None:
        """Show recovery dialog and handle the chosen action."""
        # Determine available actions based on attempt count and error type
        actions = self._determine_recovery_actions(app_error)

        # Show the error dialog
        chosen_action = self._error_dialog_manager.show_error(app_error, actions)

        # Handle the chosen action
        self._handle_recovery_action(chosen_action, app_error, context)

    def _determine_recovery_actions(self, app_error: BaseAppError) -> list[RecoveryAction]:
        """Determine available recovery actions based on error and attempt count."""
        actions = []

        # Add retry if we haven't exceeded max attempts
        if self._attempt_count < self._max_attempts and app_error.retriable:
            actions.append(RecoveryAction.RETRY)

        # Add specific actions based on error type
        if "file" in app_error.type.value.lower():
            if "permission" in app_error.code.value.lower():
                actions.append(RecoveryAction.OPEN_PERMISSIONS_HELP)
            if "not_found" in app_error.code.value.lower():
                actions.append(RecoveryAction.SELECT_ALTERNATIVE_PATH)

        elif app_error.type.value in ("validation", "config"):
            actions.append(RecoveryAction.OPEN_SETTINGS)

        # Always add report issue for high severity errors
        if app_error.severity.value in ("high", "critical"):
            actions.append(RecoveryAction.REPORT_ISSUE)

        # Always add cancel
        actions.append(RecoveryAction.CANCEL)

        return actions

    def _handle_recovery_action(self, action: RecoveryAction, app_error: BaseAppError, context: dict[str, Any]) -> None:
        """Handle the chosen recovery action."""
        self._logger.info(f"Handling recovery action: {action.value}")

        if action == RecoveryAction.RETRY:
            self._schedule_retry()
        elif action == RecoveryAction.SELECT_ALTERNATIVE_PATH:
            # This will be handled by the error dialog manager's signal
            pass
        elif action == RecoveryAction.OPEN_PERMISSIONS_HELP:
            # This will be handled by the error dialog manager's signal
            self._in_recovery = False  # Allow user to try again
        elif action == RecoveryAction.OPEN_SETTINGS:
            self.settingsRequested.emit()
            self._in_recovery = False  # Allow user to try again
        elif action == RecoveryAction.REPORT_ISSUE:
            # This will be handled by the error dialog manager's signal
            self._in_recovery = False  # Allow user to try again
        elif action == RecoveryAction.CANCEL:
            self._cancel_recovery()

    def _schedule_retry(self) -> None:
        """Schedule a retry with exponential backoff."""
        if self._attempt_count >= self._max_attempts:
            self._logger.warning(f"Max retry attempts ({self._max_attempts}) exceeded")
            self._show_final_failure_dialog()
            return

        # Calculate backoff delay
        delay_ms = min(self._max_backoff_ms, self._base_backoff_ms * (2 ** (self._attempt_count - 1)))

        self._logger.info(f"Scheduling retry in {delay_ms}ms (attempt {self._attempt_count})")

        # Start the retry timer
        self._retry_timer.start(delay_ms)

        # Emit signal to update UI with retry countdown
        self.performRetryRequested.emit(delay_ms)

    def _execute_retry(self) -> None:
        """Execute the actual retry."""
        if not self._current_config:
            self._logger.error("No configuration available for retry")
            self._cancel_recovery()
            return

        self._logger.info(f"Executing retry attempt {self._attempt_count}")
        self._in_recovery = False  # Allow new errors to be processed

        # Emit signal to restart conversion
        # The parent controller should handle this by starting a new worker
        from PySide6.QtCore import QTimer

        parent = self.parent()
        if hasattr(parent, "start_conversion"):
            QTimer.singleShot(0, lambda: parent.start_conversion(self._current_config))

    def _show_final_failure_dialog(self) -> None:
        """Show final failure dialog when max attempts are exceeded."""
        from core.errors import ErrorCode, SystemError

        final_error = SystemError(
            code=ErrorCode.BACKEND_FAILURE,
            user_message=f"Conversion failed after {self._max_attempts} attempts",
            technical_message=f"Maximum retry attempts ({self._max_attempts}) exceeded",
            context={"job_id": self._current_job_id, "final_attempt": True},
        )

        # Show dialog with limited actions (no retry)
        actions = [RecoveryAction.SELECT_ALTERNATIVE_PATH, RecoveryAction.OPEN_SETTINGS, RecoveryAction.CANCEL]
        self._error_dialog_manager.show_error(final_error, actions)

        self._cancel_recovery()

    def _cancel_recovery(self) -> None:
        """Cancel any pending recovery operations."""
        self._retry_timer.stop()
        self._in_recovery = False
        self.cancelRequested.emit()
        self._logger.info("Recovery cancelled")

    @Slot()
    def _on_retry_requested(self) -> None:
        """Handle retry request from error dialog."""
        # This is handled by _handle_recovery_action, but we can add additional logic here
        pass

    @Slot(str)
    def _on_alternative_path_requested(self, new_path: str) -> None:
        """Handle alternative path selection."""
        if not self._current_config:
            self._logger.error("No configuration available for path update")
            return

        self._logger.info(f"Alternative path selected: {new_path}")

        # Update configuration with new path
        from pathlib import Path

        self._current_config.out_dir = Path(new_path)

        # Reset attempt count since we're changing configuration
        self._attempt_count = 0
        self._in_recovery = False

        # Emit signal to restart with new configuration
        self.alternativePathSelected.emit(new_path)

    @Slot()
    def _on_settings_requested(self) -> None:
        """Handle settings dialog request."""
        self.settingsRequested.emit()

    @Slot(str)
    def _on_issue_report_requested(self, error_details: str) -> None:
        """Handle issue report request."""
        self.issueReportRequested.emit(error_details)

    def cancel_pending_recovery(self) -> None:
        """Cancel any pending recovery operations (public interface)."""
        self._cancel_recovery()

    def reset(self) -> None:
        """Reset recovery state for a new job."""
        self._retry_timer.stop()
        self._attempt_count = 0
        self._in_recovery = False
        self._current_job_id = None
        self._current_config = None
        self._logger.debug("Recovery manager reset")

    def is_in_recovery(self) -> bool:
        """Check if currently in recovery mode."""
        return self._in_recovery

    def get_attempt_count(self) -> int:
        """Get current attempt count."""
        return self._attempt_count

    def set_max_attempts(self, max_attempts: int) -> None:
        """Set maximum retry attempts."""
        self._max_attempts = max(1, max_attempts)

    def set_backoff_parameters(self, base_ms: int, max_ms: int) -> None:
        """Set backoff timing parameters."""
        self._base_backoff_ms = max(100, base_ms)
        self._max_backoff_ms = max(self._base_backoff_ms, max_ms)
