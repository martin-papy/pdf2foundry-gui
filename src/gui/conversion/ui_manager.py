"""
UI management utilities for conversion operations.

This module contains methods for managing UI state during conversions,
including progress updates, state restoration, and finalization.
"""

import logging
import uuid
from typing import TYPE_CHECKING

from core.conversion_state import ConversionState

if TYPE_CHECKING:
    from gui.main_window import MainWindow


class ConversionUIManager:
    """Manages UI state during conversion operations."""

    def __init__(self, main_window: "MainWindow") -> None:
        """Initialize the UI manager."""
        self.main_window = main_window
        self._logger = logging.getLogger(__name__)

    def _restore_idle_ui(self, reset_progress: bool = True, preserve_format: bool = False) -> None:
        """
        Restore UI to idle state after conversion completion.

        Args:
            reset_progress: Whether to reset progress bar value to 0
            preserve_format: Whether to preserve progress bar format text
        """
        try:
            # Set conversion state to idle
            self.main_window.set_conversion_state(ConversionState.IDLE)

            # Reset internal flags if they exist
            if hasattr(self.main_window, "conversion_handler"):
                handler = self.main_window.conversion_handler
                if hasattr(handler, "_in_progress"):
                    handler._in_progress = False
                if hasattr(handler, "_cancel_requested"):
                    handler._cancel_requested = False
                if hasattr(handler, "_conversion_started"):
                    handler._conversion_started = False

            # Reset progress bar if requested
            if reset_progress and hasattr(self.main_window, "progress_bar"):
                self.main_window.progress_bar.setRange(0, 100)
                self.main_window.progress_bar.setValue(0)

                # Reset format text unless preservation is requested
                if not preserve_format:
                    self.main_window.progress_bar.setFormat("")

            self._logger.debug("UI restored to idle state")

        except Exception as e:
            self._logger.error(f"Error restoring UI to idle state: {e}")

    def _finalize_conversion(self, outcome: str, details: dict | None = None) -> None:
        """
        Finalize conversion with proper cleanup and notifications.

        Args:
            outcome: Conversion outcome ('success', 'error', 'cancelled')
            details: Optional details dictionary with outcome-specific information
        """
        # Generate conversion ID if not available
        conversion_id = "unknown"
        if hasattr(self.main_window, "conversion_handler"):
            handler = self.main_window.conversion_handler
            if hasattr(handler, "_conversion_id") and handler._conversion_id:
                conversion_id = handler._conversion_id
            else:
                conversion_id = str(uuid.uuid4())[:8]

        try:
            # Check if already notified to prevent double notifications
            if hasattr(self.main_window, "conversion_handler"):
                handler = self.main_window.conversion_handler
                if hasattr(handler, "_result_notified") and handler._result_notified:
                    self._logger.debug(f"[{conversion_id}] Conversion already finalized, skipping")
                    return

                # Mark as notified
                if hasattr(handler, "_result_notified"):
                    handler._result_notified = True

            # Log the finalization
            self._logger.info(f"[{conversion_id}] Finalizing conversion with outcome: {outcome}")

            # Restore UI to appropriate state based on outcome
            if outcome == "success":
                # For successful completions, set to completed state instead of idle
                self.main_window.set_conversion_state(ConversionState.COMPLETED)
            elif outcome == "error":
                # For errors, set to error state to show the user there was an error
                self.main_window.set_conversion_state(ConversionState.ERROR)
            else:
                # For cancellations, restore to idle with preservation
                reset_progress = outcome == "cancelled"  # Only reset progress for cancellation
                preserve_format = outcome in ["error", "cancelled"]
                self._restore_idle_ui(reset_progress=reset_progress, preserve_format=preserve_format)

        except Exception as e:
            self._logger.error(f"[{conversion_id}] Error during conversion finalization: {e}")
            # Ensure UI is restored even if finalization fails
            self._restore_idle_ui()

    def _reset_progress_after_cancel(self) -> None:
        """Reset progress bar after cancellation."""
        if hasattr(self.main_window, "progress_bar"):
            self.main_window.progress_bar.setValue(0)
            self.main_window.progress_bar.setFormat("Canceled")

    def _set_conversion_state(self, is_converting: bool) -> None:
        """
        Set the conversion state.

        Args:
            is_converting: Whether conversion is currently running
        """
        if is_converting:
            self.main_window.set_conversion_state(ConversionState.RUNNING)
        else:
            self.main_window.set_conversion_state(ConversionState.IDLE)
