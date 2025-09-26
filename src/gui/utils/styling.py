"""
Shared styling utilities for the PDF2Foundry GUI application.

This module contains common styling functions and constants that can be
reused across different GUI components with accessibility compliance.
"""

from typing import Any, Protocol

from PySide6.QtGui import QColor, QFont, QFontDatabase, QTextCharFormat


class StyleableWidget(Protocol):
    """Protocol for widgets that can be styled."""

    def setStyleSheet(self, styleSheet: str) -> None: ...
    def style(self) -> Any: ...


class AccessiblePalette:
    """
    Centralized color palette with WCAG AA accessibility compliance.

    All color combinations meet minimum contrast ratio of 4.5:1 for normal text
    and 3:1 for large text (18pt+ or 14pt+ bold).
    """

    # Log level colors (WCAG AA compliant)
    LOG_INFO_TEXT = "#495057"  # Dark gray on light backgrounds
    LOG_INFO_BG = "#f8f9fa"  # Light gray background

    LOG_WARNING_TEXT = "#856404"  # Dark amber for readability
    LOG_WARNING_BG = "#fff3cd"  # Light amber background

    LOG_ERROR_TEXT = "#721c24"  # Dark red for high contrast
    LOG_ERROR_BG = "#f8d7da"  # Light red background

    # Status indicator colors
    STATUS_IDLE_COLOR = "#6c757d"  # Neutral gray
    STATUS_RUNNING_COLOR = "#fd7e14"  # Orange (high contrast)
    STATUS_COMPLETED_COLOR = "#198754"  # Green (WCAG compliant)
    STATUS_ERROR_COLOR = "#dc3545"  # Red (high contrast)

    # Search and selection colors
    SEARCH_HIGHLIGHT_BG = "#fff3cd"  # Light amber for highlights
    SEARCH_HIGHLIGHT_TEXT = "#212529"  # Dark text for contrast
    SEARCH_ACTIVE_BG = "#ffc107"  # Stronger amber for active match
    SEARCH_ACTIVE_TEXT = "#000000"  # Black text for maximum contrast

    # UI element colors
    BORDER_DEFAULT = "#dee2e6"  # Light border
    BORDER_FOCUS = "#0d6efd"  # Blue focus indicator
    BORDER_ERROR = "#dc3545"  # Error state border
    BORDER_SUCCESS = "#198754"  # Success state border

    BACKGROUND_DEFAULT = "#ffffff"  # Pure white background
    BACKGROUND_SECONDARY = "#f8f9fa"  # Light gray background
    BACKGROUND_DISABLED = "#e9ecef"  # Disabled element background

    TEXT_PRIMARY = "#212529"  # Primary text color
    TEXT_SECONDARY = "#6c757d"  # Secondary text color
    TEXT_DISABLED = "#adb5bd"  # Disabled text color

    # Button and control colors
    BUTTON_PRIMARY_BG = "#0d6efd"  # Primary button background
    BUTTON_PRIMARY_TEXT = "#ffffff"  # Primary button text
    BUTTON_SECONDARY_BG = "#6c757d"  # Secondary button background
    BUTTON_SECONDARY_TEXT = "#ffffff"  # Secondary button text

    # Drag and drop colors
    DRAG_NORMAL_BORDER = "#6c757d"  # Normal drag zone border
    DRAG_HOVER_BORDER = "#0d6efd"  # Hover state border
    DRAG_REJECT_BORDER = "#dc3545"  # Rejection state border
    DRAG_HOVER_BG = "rgba(13, 110, 253, 0.1)"  # Light blue background
    DRAG_REJECT_BG = "rgba(220, 53, 69, 0.1)"  # Light red background


class StyleSheets:
    """Collection of reusable stylesheet definitions using the accessible palette."""

    @staticmethod
    def get_status_label_style(status: str = "default") -> str:
        """Get status label stylesheet for the given status."""
        styles = {
            "success": f"""
                QLabel {{
                    color: {AccessiblePalette.STATUS_COMPLETED_COLOR};
                    font-size: 14px;
                    font-weight: bold;
                    padding: 10px;
                    background-color: {AccessiblePalette.LOG_INFO_BG};
                    border: 1px solid {AccessiblePalette.BORDER_SUCCESS};
                    border-radius: 4px;
                }}
            """,
            "error": f"""
                QLabel {{
                    color: {AccessiblePalette.LOG_ERROR_TEXT};
                    font-size: 14px;
                    font-weight: bold;
                    padding: 10px;
                    background-color: {AccessiblePalette.LOG_ERROR_BG};
                    border: 1px solid {AccessiblePalette.BORDER_ERROR};
                    border-radius: 4px;
                }}
            """,
            "warning": f"""
                QLabel {{
                    color: {AccessiblePalette.LOG_WARNING_TEXT};
                    font-size: 14px;
                    font-weight: bold;
                    padding: 10px;
                    background-color: {AccessiblePalette.LOG_WARNING_BG};
                    border: 1px solid {AccessiblePalette.LOG_WARNING_TEXT};
                    border-radius: 4px;
                }}
            """,
            "default": f"""
                QLabel {{
                    color: {AccessiblePalette.TEXT_SECONDARY};
                    font-size: 14px;
                    padding: 10px;
                    background-color: {AccessiblePalette.BACKGROUND_SECONDARY};
                    border: 1px solid {AccessiblePalette.BORDER_DEFAULT};
                    border-radius: 4px;
                }}
            """,
        }
        return styles.get(status, styles["default"])

    @staticmethod
    def get_log_console_style() -> str:
        """Get stylesheet for the log console text edit."""
        font_family = get_monospace_font().family()
        font_size = get_monospace_font().pointSize()

        return f"""
            QTextEdit#logTextEdit {{
                background-color: {AccessiblePalette.BACKGROUND_DEFAULT};
                border: 1px solid {AccessiblePalette.BORDER_DEFAULT};
                border-radius: 4px;
                font-family: '{font_family}';
                font-size: {font_size}pt;
                color: {AccessiblePalette.TEXT_PRIMARY};
                selection-background-color: {AccessiblePalette.SEARCH_HIGHLIGHT_BG};
                selection-color: {AccessiblePalette.SEARCH_HIGHLIGHT_TEXT};
            }}
            
            QTextEdit#logTextEdit:focus {{
                border: 2px solid {AccessiblePalette.BORDER_FOCUS};
            }}
        """

    @staticmethod
    def get_input_validation_style(is_valid: bool) -> str:
        """Get input validation stylesheet."""
        if is_valid:
            return f"""
                QLineEdit {{
                    border: 2px solid {AccessiblePalette.BORDER_SUCCESS};
                    background-color: {AccessiblePalette.BACKGROUND_DEFAULT};
                    color: {AccessiblePalette.TEXT_PRIMARY};
                }}
            """
        else:
            return f"""
                QLineEdit {{
                    border: 2px solid {AccessiblePalette.BORDER_ERROR};
                    background-color: {AccessiblePalette.BACKGROUND_DEFAULT};
                    color: {AccessiblePalette.TEXT_PRIMARY};
                }}
            """

    @staticmethod
    def get_button_style(button_type: str = "primary") -> str:
        """Get button stylesheet for the given type."""
        if button_type == "primary":
            return f"""
                QPushButton {{
                    background-color: {AccessiblePalette.BUTTON_PRIMARY_BG};
                    color: {AccessiblePalette.BUTTON_PRIMARY_TEXT};
                    border: 2px solid {AccessiblePalette.BUTTON_PRIMARY_BG};
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                    min-height: 20px;
                }}
                
                QPushButton:hover {{
                    background-color: #0b5ed7;
                    border-color: #0b5ed7;
                }}
                
                QPushButton:pressed {{
                    background-color: #0a58ca;
                    border-color: #0a58ca;
                }}
                
                QPushButton:disabled {{
                    background-color: {AccessiblePalette.BACKGROUND_DISABLED};
                    color: {AccessiblePalette.TEXT_DISABLED};
                    border-color: {AccessiblePalette.BORDER_DEFAULT};
                }}
                
                QPushButton:focus {{
                    outline: 2px solid {AccessiblePalette.BORDER_FOCUS};
                    outline-offset: 2px;
                }}
            """
        else:  # secondary
            return f"""
                QPushButton {{
                    background-color: {AccessiblePalette.BUTTON_SECONDARY_BG};
                    color: {AccessiblePalette.BUTTON_SECONDARY_TEXT};
                    border: 2px solid {AccessiblePalette.BUTTON_SECONDARY_BG};
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                    min-height: 20px;
                }}
                
                QPushButton:hover {{
                    background-color: #5c636a;
                    border-color: #5c636a;
                }}
                
                QPushButton:pressed {{
                    background-color: #565e64;
                    border-color: #565e64;
                }}
                
                QPushButton:disabled {{
                    background-color: {AccessiblePalette.BACKGROUND_DISABLED};
                    color: {AccessiblePalette.TEXT_DISABLED};
                    border-color: {AccessiblePalette.BORDER_DEFAULT};
                }}
                
                QPushButton:focus {{
                    outline: 2px solid {AccessiblePalette.BORDER_FOCUS};
                    outline-offset: 2px;
                }}
            """


class Colors:
    """Legacy color constants for backward compatibility."""

    # Redirect to new palette
    SUCCESS_TEXT = AccessiblePalette.STATUS_COMPLETED_COLOR
    SUCCESS_BG = AccessiblePalette.LOG_INFO_BG
    SUCCESS_BORDER = AccessiblePalette.BORDER_SUCCESS

    ERROR_TEXT = AccessiblePalette.LOG_ERROR_TEXT
    ERROR_BG = AccessiblePalette.LOG_ERROR_BG
    ERROR_BORDER = AccessiblePalette.BORDER_ERROR

    DEFAULT_TEXT = AccessiblePalette.TEXT_SECONDARY
    DEFAULT_BG = AccessiblePalette.BACKGROUND_SECONDARY
    DEFAULT_BORDER = AccessiblePalette.BORDER_DEFAULT

    VALID_BORDER = AccessiblePalette.BORDER_SUCCESS
    VALID_BG = AccessiblePalette.BACKGROUND_DEFAULT

    INVALID_BORDER = AccessiblePalette.BORDER_ERROR
    INVALID_BG = AccessiblePalette.BACKGROUND_DEFAULT

    REJECT_COLOR = AccessiblePalette.DRAG_REJECT_BORDER


def get_monospace_font() -> QFont:
    """
    Get a DPI-aware monospace font suitable for log display.

    Returns:
        QFont configured for optimal readability
    """
    font = QFont()

    # Try to get system monospace font
    font_db = QFontDatabase()
    monospace_families = font_db.families(QFontDatabase.WritingSystem.Latin)

    # Preferred monospace fonts in order of preference
    preferred_fonts = [
        "SF Mono",  # macOS system font
        "Consolas",  # Windows
        "Ubuntu Mono",  # Ubuntu
        "DejaVu Sans Mono",  # Linux
        "Courier New",  # Fallback
        "monospace",  # Generic fallback
    ]

    selected_family = "monospace"  # Default fallback
    for preferred in preferred_fonts:
        if preferred in monospace_families:
            selected_family = preferred
            break

    font.setFamily(selected_family)
    font.setStyleHint(QFont.StyleHint.Monospace)

    # Set DPI-aware size (12pt is good for readability)
    font.setPointSize(12)

    return font


def get_log_text_format(level: str) -> QTextCharFormat:
    """
    Get QTextCharFormat for log levels with accessible colors.

    Args:
        level: Log level (INFO, WARNING, ERROR)

    Returns:
        QTextCharFormat with appropriate styling
    """
    text_format = QTextCharFormat()

    if level == "WARNING":
        text_format.setForeground(QColor(AccessiblePalette.LOG_WARNING_TEXT))
        font = get_monospace_font()
        font.setBold(True)
        text_format.setFont(font)
    elif level == "ERROR":
        text_format.setForeground(QColor(AccessiblePalette.LOG_ERROR_TEXT))
        font = get_monospace_font()
        font.setBold(True)
        text_format.setFont(font)
    else:  # INFO or default
        text_format.setForeground(QColor(AccessiblePalette.LOG_INFO_TEXT))
        text_format.setFont(get_monospace_font())

    return text_format


def get_status_indicator_color(status_state: str) -> str:
    """
    Get color for status indicator based on state.

    Args:
        status_state: Status state name (IDLE, RUNNING, COMPLETED, ERROR)

    Returns:
        Color hex string
    """
    status_colors = {
        "IDLE": AccessiblePalette.STATUS_IDLE_COLOR,
        "RUNNING": AccessiblePalette.STATUS_RUNNING_COLOR,
        "COMPLETED": AccessiblePalette.STATUS_COMPLETED_COLOR,
        "ERROR": AccessiblePalette.STATUS_ERROR_COLOR,
    }
    return status_colors.get(status_state, AccessiblePalette.STATUS_IDLE_COLOR)


def apply_status_style(widget: StyleableWidget, status: str = "default") -> None:
    """
    Apply status-based styling to a widget.

    Args:
        widget: The widget to style
        status: Status type ("default", "success", "error", "warning")
    """
    widget.setStyleSheet(StyleSheets.get_status_label_style(status))


def apply_validation_style(widget: StyleableWidget, is_valid: bool) -> None:
    """
    Apply validation-based styling to an input widget.

    Args:
        widget: The input widget to style
        is_valid: Whether the input is valid
    """
    widget.setStyleSheet(StyleSheets.get_input_validation_style(is_valid))

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
        return f"""
            QLabel#dragZone {{
                border: 2px dashed {AccessiblePalette.DRAG_HOVER_BORDER};
                border-radius: 12px;
                background-color: {AccessiblePalette.DRAG_HOVER_BG};
                color: {AccessiblePalette.TEXT_PRIMARY};
                font-size: 14px;
                font-weight: bold;
                padding: 24px;
                min-height: 120px;
            }}
        """
    elif state == "reject":
        return f"""
            QLabel#dragZone {{
                border: 2px dashed {AccessiblePalette.DRAG_REJECT_BORDER};
                border-radius: 12px;
                background-color: {AccessiblePalette.DRAG_REJECT_BG};
                color: {AccessiblePalette.DRAG_REJECT_BORDER};
                font-size: 14px;
                font-weight: bold;
                padding: 24px;
                min-height: 120px;
            }}
        """
    else:  # normal
        return f"""
            QLabel#dragZone {{
                border: 2px dashed {AccessiblePalette.DRAG_NORMAL_BORDER};
                border-radius: 12px;
                background-color: rgba(108, 117, 125, 0.1);
                color: {AccessiblePalette.TEXT_SECONDARY};
                font-size: 14px;
                font-weight: normal;
                padding: 24px;
                min-height: 120px;
            }}
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


def create_search_highlight_format(is_active: bool = False) -> QTextCharFormat:
    """
    Create QTextCharFormat for search highlighting.

    Args:
        is_active: Whether this is the currently active match

    Returns:
        QTextCharFormat with appropriate highlighting
    """
    highlight_format = QTextCharFormat()

    if is_active:
        highlight_format.setBackground(QColor(AccessiblePalette.SEARCH_ACTIVE_BG))
        highlight_format.setForeground(QColor(AccessiblePalette.SEARCH_ACTIVE_TEXT))
    else:
        highlight_format.setBackground(QColor(AccessiblePalette.SEARCH_HIGHLIGHT_BG))
        highlight_format.setForeground(QColor(AccessiblePalette.SEARCH_HIGHLIGHT_TEXT))

    return highlight_format
