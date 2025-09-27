"""
Custom validators for PDF2Foundry GUI input fields.

This module provides QValidator subclasses and custom validation functions
for different types of input fields.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, ClassVar

from PySide6.QtCore import QLocale, QRegularExpression
from PySide6.QtGui import QDoubleValidator, QIntValidator, QRegularExpressionValidator, QValidator
from PySide6.QtWidgets import QWidget

from core.errors import ErrorCode, ValidationError


class ModuleIdValidator(QRegularExpressionValidator):
    """
    Validator for Foundry VTT module IDs.

    Ensures module IDs follow the pattern: lowercase letters, numbers,
    hyphens, and underscores, 3-64 characters long.
    """

    # Reserved module IDs that should not be allowed
    RESERVED_IDS: ClassVar[set[str]] = {
        "core",
        "system",
        "world",
        "module",
        "foundry",
        "vtt",
        "admin",
        "api",
        "data",
        "public",
        "scripts",
        "styles",
        "templates",
        "lang",
        "fonts",
        "sounds",
        "ui",
        "common",
    }

    def __init__(self, parent: QWidget | None = None):
        # Pattern: 3-64 characters, lowercase letters, numbers, hyphens, underscores
        # Cannot start or end with hyphen or underscore
        # For 3 chars: all alphanumeric, for 4+ chars: alphanumeric at start/end
        pattern = QRegularExpression(r"^([a-z0-9]{3}|[a-z0-9][a-z0-9_-]{1,62}[a-z0-9])$")
        super().__init__(pattern, parent)

    def validate(self, input_text: str, pos: int) -> tuple[QValidator.State, str, int]:
        """Validate module ID input."""
        # First check the regex pattern
        result = super().validate(input_text, pos)
        # Extract components with explicit typing
        state = QValidator.State(result[0])  # type: ignore[index]
        text = str(result[1])  # type: ignore[index]
        new_pos = int(result[2])  # type: ignore[index]

        if state == QValidator.State.Acceptable and text.lower() in self.RESERVED_IDS:
            return QValidator.State.Invalid, text, new_pos

        return state, text, new_pos

    def fixup(self, input_text: str) -> str:
        """Fix up the input by converting to lowercase and replacing invalid characters."""
        # Convert to lowercase
        fixed = input_text.lower()

        # Replace spaces and other invalid characters with hyphens
        fixed = re.sub(r"[^a-z0-9_-]", "-", fixed)

        # Remove consecutive hyphens
        fixed = re.sub(r"-+", "-", fixed)

        # Remove leading/trailing hyphens
        fixed = fixed.strip("-")

        # Ensure minimum length
        if len(fixed) < 3:
            fixed = fixed.ljust(3, "0")

        # Ensure maximum length
        if len(fixed) > 64:
            fixed = fixed[:64]

        return fixed


class ModuleTitleValidator(QValidator):
    """
    Validator for module titles.

    Ensures titles are non-empty and within reasonable length limits.
    """

    def __init__(self, parent: QWidget | None = None, max_length: int = 128):
        super().__init__(parent)
        self.max_length = max_length

    def validate(self, input_text: str, pos: int) -> tuple[QValidator.State, str, int]:
        """Validate module title input."""
        text = input_text.strip()

        if not text:
            return QValidator.State.Intermediate, input_text, pos

        if len(text) > self.max_length:
            return QValidator.State.Invalid, input_text, pos

        return QValidator.State.Acceptable, input_text, pos

    def fixup(self, input_text: str) -> str:
        """Fix up the input by trimming whitespace and limiting length."""
        fixed = input_text.strip()

        if len(fixed) > self.max_length:
            fixed = fixed[: self.max_length].strip()

        return fixed


class PathWritableValidator(QValidator):
    """
    Validator for file paths that need to be writable directories.

    Checks that the path exists, is a directory, and is writable.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

    def validate(self, input_text: str, pos: int) -> tuple[QValidator.State, str, int]:
        """Validate path input."""
        if not input_text.strip():
            return QValidator.State.Intermediate, input_text, pos

        try:
            path = Path(input_text.strip()).expanduser().resolve()

            # Check if path exists
            if not path.exists():
                return QValidator.State.Intermediate, input_text, pos

            # Check if it's a directory
            if not path.is_dir():
                return QValidator.State.Invalid, input_text, pos

            # Check if it's writable
            if not os.access(path, os.W_OK):
                return QValidator.State.Invalid, input_text, pos

            return QValidator.State.Acceptable, input_text, pos

        except (OSError, ValueError):
            return QValidator.State.Invalid, input_text, pos

    def fixup(self, input_text: str) -> str:
        """Fix up the input by normalizing the path."""
        try:
            path = Path(input_text.strip()).expanduser()
            return str(path)
        except (OSError, ValueError):
            return input_text.strip()


class NumericRangeValidator(QIntValidator):
    """
    Enhanced integer validator with custom range validation.
    """

    def __init__(self, minimum: int, maximum: int, parent: QWidget | None = None):
        # Set a very wide range for the base validator to avoid premature Invalid states
        super().__init__(-999999, 999999, parent)
        self._custom_min = minimum
        self._custom_max = maximum

    def bottom(self) -> int:
        """Return the custom minimum value."""
        return self._custom_min

    def top(self) -> int:
        """Return the custom maximum value."""
        return self._custom_max

    def validate(self, input_text: str, pos: int) -> tuple[QValidator.State, str, int]:
        """Validate numeric input with range checking."""
        if not input_text.strip():
            return QValidator.State.Intermediate, input_text, pos

        result = super().validate(input_text, pos)
        # Extract components with explicit typing
        state = QValidator.State(result[0])  # type: ignore[index]
        text = str(result[1])  # type: ignore[index]
        new_pos = int(result[2])  # type: ignore[index]

        if state == QValidator.State.Acceptable:
            try:
                value = int(text)
                if not (self._custom_min <= value <= self._custom_max):
                    return QValidator.State.Intermediate, text, new_pos
            except ValueError:
                return QValidator.State.Invalid, text, new_pos

        return state, text, new_pos


class DecimalRangeValidator(QDoubleValidator):
    """
    Enhanced double validator with custom range validation and locale handling.
    """

    def __init__(self, minimum: float, maximum: float, decimals: int = 2, parent: QWidget | None = None):
        # Set a very wide range for the base validator to avoid premature Invalid states
        super().__init__(-999999.0, 999999.0, decimals, parent)
        self._custom_min = minimum
        self._custom_max = maximum

        # Use dot notation for consistency
        self.setNotation(QDoubleValidator.Notation.StandardNotation)

        # Set locale to ensure dot as decimal separator
        locale = QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)
        self.setLocale(locale)

    def bottom(self) -> float:
        """Return the custom minimum value."""
        return self._custom_min

    def top(self) -> float:
        """Return the custom maximum value."""
        return self._custom_max

    def validate(self, input_text: str, pos: int) -> tuple[QValidator.State, str, int]:
        """Validate decimal input with range checking."""
        if not input_text.strip():
            return QValidator.State.Intermediate, input_text, pos

        result = super().validate(input_text, pos)
        # Extract components with explicit typing
        state = QValidator.State(result[0])  # type: ignore[index]
        text = str(result[1])  # type: ignore[index]
        new_pos = int(result[2])  # type: ignore[index]

        if state == QValidator.State.Acceptable:
            try:
                value = float(text)
                if not (self._custom_min <= value <= self._custom_max):
                    return QValidator.State.Intermediate, text, new_pos
            except ValueError:
                return QValidator.State.Invalid, text, new_pos

        return state, text, new_pos


def create_validation_error(field: str, message: str, value: Any = None) -> ValidationError:
    """
    Create a ValidationError for logging purposes.

    Args:
        field: Field name that failed validation
        message: Validation error message
        value: The invalid value

    Returns:
        ValidationError instance
    """
    # Determine error code based on message content
    code = ErrorCode.INVALID_INPUT

    if "required" in message.lower():
        code = ErrorCode.REQUIRED_FIELD_MISSING
    elif "format" in message.lower() or "pattern" in message.lower():
        code = ErrorCode.INVALID_FORMAT
    elif "range" in message.lower() or "length" in message.lower():
        code = ErrorCode.VALUE_OUT_OF_RANGE
    elif "path" in message.lower() and "not found" in message.lower():
        code = ErrorCode.FILE_NOT_FOUND
    elif "permission" in message.lower() or "writable" in message.lower():
        code = ErrorCode.PERMISSION_DENIED

    return ValidationError(
        code=code,
        user_message=message,
        field=field,
        technical_message=f"Validation failed for field '{field}': {message}",
        context={"value": value} if value is not None else {},
    )
