"""
Status indicator widget and state management for the main window.

This module provides status state definitions and a status indicator widget
for displaying the current application state.
"""

from enum import Enum

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from gui.utils.styling import AccessiblePalette, get_status_indicator_color


class StatusState(Enum):
    """Status indicator states with accessible colors and descriptions."""

    IDLE = ("Idle", "Ready to convert PDF files")
    RUNNING = ("Running", "Conversion in progress")
    COMPLETED = ("Completed", "Conversion completed successfully")
    ERROR = ("Error", "Conversion failed with errors")

    def __init__(self, display_name: str, description: str) -> None:
        self.display_name = display_name
        self.description = description

    @property
    def color(self) -> str:
        return get_status_indicator_color(self.name)


class StatusIndicatorWidget(QWidget):
    """
    Widget for displaying the current application status.

    Shows a colored dot and status text with accessibility support.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the status indicator widget."""
        super().__init__(parent)
        self._current_state = StatusState.IDLE
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setObjectName("statusIndicator")
        self.setAccessibleName("Conversion status")
        self.setAccessibleDescription("Shows the current conversion status")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Status dot
        self.status_dot = QLabel()
        self.status_dot.setFixedSize(12, 12)
        self.status_dot.setAccessibleName("Status indicator dot")
        layout.addWidget(self.status_dot)

        # Status text
        self.status_text = QLabel()
        self.status_text.setAccessibleName("Status text")
        layout.addWidget(self.status_text)

        # Set initial state
        self.set_status(StatusState.IDLE)

    def set_status(self, state: StatusState) -> None:
        """
        Set the current status state.

        Args:
            state: The new status state
        """
        self._current_state = state

        # Update dot color and styling
        self.status_dot.setStyleSheet(
            f"""
            QLabel {{
                border-radius: 6px;
                background-color: {state.color};
                border: 1px solid {AccessiblePalette.BORDER_DEFAULT};
            }}
        """
        )

        # Update text and accessibility
        self.status_text.setText(state.display_name)

        # Update accessible descriptions for screen readers
        self.status_dot.setAccessibleDescription(f"Status: {state.display_name}")
        self.status_text.setAccessibleDescription(state.description)
        self.setToolTip(f"{state.display_name}: {state.description}")

    def get_status(self) -> StatusState:
        """Get the current status state."""
        return self._current_state


class StatusManager:
    """
    Manages status state transitions and persistence.

    Provides methods for updating status and handling state changes.
    """

    def __init__(self, status_widget: StatusIndicatorWidget) -> None:
        """
        Initialize the status manager.

        Args:
            status_widget: The status indicator widget to manage
        """
        self._status_widget = status_widget
        self._settings = QSettings()

    def set_status(self, state: StatusState) -> None:
        """
        Set the current status state.

        Args:
            state: The new status state
        """
        self._status_widget.set_status(state)

        # Optionally persist the status (for debugging/recovery)
        self._settings.setValue("ui/lastStatus", state.name)

    def get_status(self) -> StatusState:
        """Get the current status state."""
        return self._status_widget.get_status()

    def reset_to_idle(self) -> None:
        """Reset status to idle state."""
        self.set_status(StatusState.IDLE)

    def set_running(self) -> None:
        """Set status to running state."""
        self.set_status(StatusState.RUNNING)

    def set_completed(self) -> None:
        """Set status to completed state."""
        self.set_status(StatusState.COMPLETED)

    def set_error(self) -> None:
        """Set status to error state."""
        self.set_status(StatusState.ERROR)
