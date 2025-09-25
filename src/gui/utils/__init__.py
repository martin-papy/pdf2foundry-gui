"""
GUI-specific utilities for the PDF2Foundry application.

This module contains utility functions and classes that are specific
to the GUI implementation.
"""

from .styling import (
    Colors,
    StyleSheets,
    apply_status_style,
    apply_validation_style,
    create_drag_zone_stylesheet,
    get_common_form_layout_config,
)

__all__ = [
    "StyleSheets",
    "Colors",
    "apply_status_style",
    "apply_validation_style",
    "create_drag_zone_stylesheet",
    "get_common_form_layout_config",
]
