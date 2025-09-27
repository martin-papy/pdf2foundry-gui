"""
Real-time input validation manager for PDF2Foundry GUI.

This module provides centralized input validation with debouncing,
error styling, and integration with the error handling system.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QValidator
from PySide6.QtWidgets import QLineEdit, QWidget

from core.error_handler import get_error_handler

from .validators import create_validation_error


class FieldValidator:
    """Configuration for a single field's validation."""

    def __init__(
        self,
        widget: QWidget,
        validator: QValidator | Callable[[str], tuple[bool, str]],
        required: bool = True,
        helper_text: str | None = None,
    ):
        self.widget = widget
        self.validator = validator
        self.required = required
        self.helper_text = helper_text
        self.last_value = ""
        self.last_error_message = ""
        self.is_valid = not required  # Start as valid if not required
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._validate)

    def _validate(self) -> None:
        """Perform the actual validation."""
        # This will be set by the InputValidator
        pass


class InputValidator(QObject):
    """
    Centralized real-time input validation manager.

    Provides debounced validation, error styling, and integration
    with the error handling system.
    """

    # Signals
    fieldValidityChanged = Signal(str, bool, str)  # key, valid, message
    overallValidityChanged = Signal(bool)  # overall_valid

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._logger = logging.getLogger(__name__)
        self._fields: dict[str, FieldValidator] = {}
        self._external_sources: dict[str, tuple[Signal, Callable[[], tuple[bool, str]] | None]] = {}
        self._external_validity: dict[str, bool] = {}
        self._debounce_delay = 200  # milliseconds
        self._error_handler = get_error_handler()

    def register_field(
        self,
        key: str,
        widget: QWidget,
        validator: QValidator | Callable[[str], tuple[bool, str]],
        required: bool = True,
        helper_text: str | None = None,
    ) -> None:
        """
        Register a field for validation.

        Args:
            key: Unique identifier for the field
            widget: The input widget to validate
            validator: QValidator instance or callable that returns (valid, message)
            required: Whether the field is required
            helper_text: Optional helper text to show
        """
        field_validator = FieldValidator(widget, validator, required, helper_text)
        validate_func = lambda: self._validate_field(key)  # noqa: E731
        field_validator.timer.timeout.connect(validate_func)

        self._fields[key] = field_validator

        # Connect to widget signals
        if isinstance(widget, QLineEdit):
            widget.textChanged.connect(lambda: self._schedule_validation(key))
            widget.editingFinished.connect(lambda: self._validate_field_immediately(key))

        # Store original tooltip (using dynamic attribute)
        if hasattr(widget, "toolTip") and widget.toolTip():
            # Store in a way that mypy can understand
            widget.__dict__["_original_tooltip"] = widget.toolTip()

        # Initial validation
        self._validate_field(key)

    def register_external_source(
        self,
        key: str,
        signal: Signal,
        message_provider: Callable[[], tuple[bool, str]] | None = None,
    ) -> None:
        """
        Register an external validation source.

        Args:
            key: Unique identifier for the source
            signal: Signal that indicates validity change
            message_provider: Optional function to get current validity and message
        """
        self._external_sources[key] = (signal, message_provider)
        self._external_validity[key] = True  # Start as valid

        # Connect to the signal
        if message_provider:
            signal.connect(lambda valid, msg: self._handle_external_validity(key, valid, msg))  # type: ignore[attr-defined]
        else:
            signal.connect(lambda valid: self._handle_external_validity(key, valid, ""))  # type: ignore[attr-defined]

    def _schedule_validation(self, key: str) -> None:
        """Schedule validation for a field with debouncing."""
        if key not in self._fields:
            return

        field = self._fields[key]
        field.timer.start(self._debounce_delay)

    def _validate_field_immediately(self, key: str) -> None:
        """Validate a field immediately (bypass debouncing)."""
        if key not in self._fields:
            return

        field = self._fields[key]
        field.timer.stop()  # Cancel any pending validation
        self._validate_field(key)

    def _validate_field(self, key: str) -> None:
        """Perform validation for a specific field."""
        if key not in self._fields:
            return

        field = self._fields[key]
        widget = field.widget

        # Get current value
        current_value = ""
        if isinstance(widget, QLineEdit):
            current_value = widget.text()

        # Skip if value hasn't changed
        if current_value == field.last_value and field.last_error_message:
            return

        field.last_value = current_value

        # Perform validation
        is_valid, error_message = self._perform_validation(field, current_value)

        # Update field state
        field.is_valid = is_valid

        # Only update UI and emit signals if the error message changed
        if error_message != field.last_error_message:
            field.last_error_message = error_message

            # Update UI styling
            self._update_field_styling(widget, is_valid, error_message)

            # Emit field validity signal
            self.fieldValidityChanged.emit(key, is_valid, error_message)

            # Log validation error if persistent
            if not is_valid and error_message:
                validation_error = create_validation_error(key, error_message, current_value)
                self._error_handler.handle(validation_error)

        # Check overall validity
        self._check_overall_validity()

    def _perform_validation(self, field: FieldValidator, value: str) -> tuple[bool, str]:
        """Perform the actual validation logic."""
        # Check if required field is empty
        if field.required and not value.strip():
            return False, "This field is required"

        # If empty and not required, it's valid
        if not value.strip() and not field.required:
            return True, ""

        # Use the validator
        if isinstance(field.validator, QValidator):
            result = field.validator.validate(value, 0)
            # Extract state with explicit typing
            state = QValidator.State(result[0])  # type: ignore[index]
            if state == QValidator.State.Acceptable:
                return True, ""
            elif state == QValidator.State.Invalid:
                return False, self._get_validator_error_message(field.validator, value)
            else:  # Intermediate
                return False, "Input is incomplete"
        else:
            # Custom callable validator
            try:
                return field.validator(value)
            except Exception as e:
                self._logger.error(f"Validation error for field: {e}")
                # Also handle the exception through the error handler
                validation_error = create_validation_error("validation", str(e), value)
                self._error_handler.handle(validation_error)
                return False, "Validation error occurred"

    def _get_validator_error_message(self, validator: QValidator, value: str) -> str:
        """Get an appropriate error message for a validator."""
        validator_type = type(validator).__name__

        if "ModuleId" in validator_type:
            return "Module ID must be 3-64 characters, lowercase letters, numbers, hyphens, and underscores only"
        elif "ModuleTitle" in validator_type:
            return "Module title must be 1-128 characters long"
        elif "PathWritable" in validator_type:
            return "Path must be a writable directory"
        elif (
            "NumericRange" in validator_type
            or "IntValidator" in validator_type
            or "DecimalRange" in validator_type
            or "DoubleValidator" in validator_type
        ):
            # Try to get range information
            try:
                bottom = getattr(validator, "bottom", lambda: "min")()
                top = getattr(validator, "top", lambda: "max")()
                return f"Value must be between {bottom} and {top}"
            except Exception:
                return "Value is out of range"
        else:
            return "Invalid input format"

    def _update_field_styling(self, widget: QWidget, is_valid: bool, error_message: str) -> None:
        """Update the styling of a field based on validation state."""
        # Block signals to prevent recursion
        widget.blockSignals(True)

        try:
            if is_valid:
                self._clear_field_error(widget)
            else:
                self._set_field_error(widget, error_message)
        finally:
            widget.blockSignals(False)

    def _set_field_error(self, widget: QWidget, message: str) -> None:
        """Mark a field as having an error and show feedback."""
        widget.setProperty("hasError", True)
        widget.setToolTip(f"Error: {message}")
        widget.style().polish(widget)  # Refresh styling

    def _clear_field_error(self, widget: QWidget) -> None:
        """Clear error state from a field."""
        widget.setProperty("hasError", False)

        # Restore original tooltip if it exists
        if hasattr(widget, "_original_tooltip"):
            widget.setToolTip(widget._original_tooltip)
        else:
            widget.setToolTip("")

        widget.style().polish(widget)  # Refresh styling

    def _handle_external_validity(self, key: str, valid: bool, message: str = "") -> None:
        """Handle validity change from external source."""
        self._external_validity[key] = valid
        self.fieldValidityChanged.emit(key, valid, message)
        self._check_overall_validity()

    def _check_overall_validity(self) -> None:
        """Check overall validation state and emit signal if changed."""
        # Check all registered fields
        all_fields_valid = all(field.is_valid for field in self._fields.values())

        # Check all external sources
        all_external_valid = all(self._external_validity.values())

        overall_valid = all_fields_valid and all_external_valid

        # Emit signal
        self.overallValidityChanged.emit(overall_valid)

    def validate_now(self, key: str) -> bool:
        """
        Validate a specific field immediately.

        Args:
            key: Field identifier

        Returns:
            True if valid, False otherwise
        """
        if key in self._fields:
            self._validate_field_immediately(key)
            return self._fields[key].is_valid
        return True

    def validate_all(self) -> bool:
        """
        Validate all registered fields immediately.

        Returns:
            True if all fields are valid, False otherwise
        """
        for key in self._fields:
            self._validate_field_immediately(key)

        all_valid = all(field.is_valid for field in self._fields.values())
        all_external_valid = all(self._external_validity.values())

        return all_valid and all_external_valid

    def force_validate_before_convert(self) -> bool:
        """
        Force validation of all fields before conversion starts.

        Returns:
            True if all fields are valid and conversion can proceed
        """
        return self.validate_all()

    def is_field_valid(self, key: str) -> bool:
        """
        Check if a specific field is valid.

        Args:
            key: Field identifier

        Returns:
            True if valid, False otherwise
        """
        if key in self._fields:
            return self._fields[key].is_valid
        if key in self._external_validity:
            return self._external_validity[key]
        return True

    def get_field_error(self, key: str) -> str:
        """
        Get the error message for a specific field.

        Args:
            key: Field identifier

        Returns:
            Error message or empty string if valid
        """
        if key in self._fields:
            return self._fields[key].last_error_message
        return ""

    def cleanup(self) -> None:
        """Clean up resources and disconnect signals."""
        for field in self._fields.values():
            field.timer.stop()
            field.timer.deleteLater()

        self._fields.clear()
        self._external_sources.clear()
        self._external_validity.clear()
