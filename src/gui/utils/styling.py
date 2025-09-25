"""
Shared styling utilities for the PDF2Foundry GUI application.

This module contains common styling functions and constants that can be
reused across different GUI components.
"""

from typing import Any, Protocol


class StyleableWidget(Protocol):
    """Protocol for widgets that can be styled."""

    def setStyleSheet(self, styleSheet: str) -> None: ...
    def style(self) -> Any: ...


class StyleSheets:
    """Collection of reusable stylesheet definitions."""

    # Status label styles
    STATUS_DEFAULT = """
        QLabel {
            color: #666666;
            font-size: 14px;
            padding: 8px;
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 4px;
        }
    """

    STATUS_SUCCESS = """
        QLabel {
            color: #155724;
            font-size: 14px;
            font-weight: bold;
            padding: 8px;
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 4px;
        }
    """

    STATUS_ERROR = """
        QLabel {
            color: #721c24;
            font-size: 14px;
            font-weight: bold;
            padding: 8px;
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            border-radius: 4px;
        }
    """

    # Input validation styles
    INPUT_VALID = """
        QLineEdit {
            border: 1px solid #28a745;
            background-color: #f8fff8;
        }
    """

    INPUT_INVALID = """
        QLineEdit {
            border: 1px solid #dc3545;
            background-color: #fff8f8;
        }
    """


class Colors:
    """Collection of color constants used throughout the application."""

    # Status colors
    SUCCESS_TEXT = "#155724"
    SUCCESS_BG = "#d4edda"
    SUCCESS_BORDER = "#c3e6cb"

    ERROR_TEXT = "#721c24"
    ERROR_BG = "#f8d7da"
    ERROR_BORDER = "#f5c6cb"

    DEFAULT_TEXT = "#666666"
    DEFAULT_BG = "#f8f9fa"
    DEFAULT_BORDER = "#e9ecef"

    # Validation colors
    VALID_BORDER = "#28a745"
    VALID_BG = "#f8fff8"

    INVALID_BORDER = "#dc3545"
    INVALID_BG = "#fff8f8"

    # Drag and drop colors
    REJECT_COLOR = "#d32f2f"


def apply_status_style(widget: StyleableWidget, status: str = "default") -> None:
    """
    Apply status-based styling to a widget.

    Args:
        widget: The widget to style
        status: Status type ("default", "success", "error")
    """
    if status == "success":
        widget.setStyleSheet(StyleSheets.STATUS_SUCCESS)
    elif status == "error":
        widget.setStyleSheet(StyleSheets.STATUS_ERROR)
    else:
        widget.setStyleSheet(StyleSheets.STATUS_DEFAULT)


def apply_validation_style(widget: StyleableWidget, is_valid: bool) -> None:
    """
    Apply validation-based styling to an input widget.

    Args:
        widget: The input widget to style
        is_valid: Whether the input is valid
    """
    if is_valid:
        widget.setStyleSheet(StyleSheets.INPUT_VALID)
    else:
        widget.setStyleSheet(StyleSheets.INPUT_INVALID)

    # Force style refresh
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def create_drag_zone_stylesheet(state: str = "normal") -> str:
    """
    Create a stylesheet for drag-and-drop zones based on state.

    Args:
        state: The current state ("normal", "hover", "reject")

    Returns:
        CSS stylesheet string
    """
    if state == "hover":
        return """
            QLabel#dragZone {
                border: 2px dashed palette(highlight);
                border-radius: 12px;
                background-color: rgba(0, 120, 212, 30);
                color: palette(highlighted-text);
                font-size: 14px;
                font-weight: bold;
                padding: 24px;
                min-height: 120px;
            }
        """
    elif state == "reject":
        return f"""
            QLabel#dragZone {{
                border: 2px dashed {Colors.REJECT_COLOR};
                border-radius: 12px;
                background-color: rgba(211, 47, 47, 20);
                color: {Colors.REJECT_COLOR};
                font-size: 14px;
                font-weight: bold;
                padding: 24px;
                min-height: 120px;
            }}
        """
    else:  # normal
        return """
            QLabel#dragZone {
                border: 2px dashed palette(mid);
                border-radius: 12px;
                background-color: rgba(128, 128, 128, 20);
                color: palette(window-text);
                font-size: 14px;
                font-weight: normal;
                padding: 24px;
                min-height: 120px;
            }
        """


def get_common_form_layout_config() -> dict[str, Any]:
    """
    Get common configuration for form layouts.

    Returns:
        Dictionary with layout configuration parameters
    """
    return {
        "field_growth_policy": "ExpandingFieldsGrow",
        "label_alignment": "AlignRight",
        "margins": (12, 12, 12, 12),
        "spacing": 12,
    }
