"""
Tests for InputValidator basic functionality and field validation.
"""

from unittest.mock import patch

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLineEdit

from gui.validation.input_validator import FieldValidator, InputValidator


class TestFieldValidator:
    """Test the FieldValidator class."""

    def test_initialization_with_qvalidator(self, mock_validator):
        """Test initialization with QValidator."""
        field_validator = FieldValidator(mock_validator)
        assert field_validator.validator is mock_validator
        assert field_validator.callable_validator is None

    def test_initialization_with_callable(self, mock_callable_validator):
        """Test initialization with callable validator."""
        field_validator = FieldValidator(mock_callable_validator)
        assert field_validator.validator is None
        assert field_validator.callable_validator is mock_callable_validator

    def test_validate_with_qvalidator_valid(self, mock_validator):
        """Test validation with QValidator returning valid."""
        field_validator = FieldValidator(mock_validator)
        result = field_validator.validate("test_value")
        assert result is True

    def test_validate_with_qvalidator_invalid(self, mock_invalid_validator):
        """Test validation with QValidator returning invalid."""
        field_validator = FieldValidator(mock_invalid_validator)
        result = field_validator.validate("test_value")
        assert result is False

    def test_validate_with_callable_valid(self, mock_callable_validator):
        """Test validation with callable validator returning valid."""
        field_validator = FieldValidator(mock_callable_validator)
        result = field_validator.validate("test_value")
        assert result is True

    def test_validate_with_callable_invalid(self, mock_invalid_callable_validator):
        """Test validation with callable validator raising exception."""
        field_validator = FieldValidator(mock_invalid_callable_validator)
        result = field_validator.validate("test_value")
        assert result is False

    def test_validate_with_callable_exception_handling(self):
        """Test validation with callable raising unexpected exception."""

        def failing_validator(value):
            raise RuntimeError("Unexpected error")

        field_validator = FieldValidator(failing_validator)
        result = field_validator.validate("test_value")
        assert result is False

    def test_get_error_message_qvalidator(self, mock_invalid_validator):
        """Test getting error message from QValidator."""
        field_validator = FieldValidator(mock_invalid_validator)
        field_validator.validate("test_value")
        error_msg = field_validator.get_error_message()
        assert "Invalid input" in error_msg

    def test_get_error_message_callable(self, mock_invalid_callable_validator):
        """Test getting error message from callable validator."""
        field_validator = FieldValidator(mock_invalid_callable_validator)
        field_validator.validate("test_value")
        error_msg = field_validator.get_error_message()
        assert error_msg == "Invalid input"

    def test_get_error_message_no_error(self, mock_validator):
        """Test getting error message when no error occurred."""
        field_validator = FieldValidator(mock_validator)
        field_validator.validate("test_value")
        error_msg = field_validator.get_error_message()
        assert error_msg == ""


class TestInputValidatorInitialization:
    """Test InputValidator initialization."""

    def test_initialization(self):
        """Test basic initialization."""
        validator = InputValidator()
        assert validator._debounce_timer is not None
        assert isinstance(validator._debounce_timer, QTimer)
        assert validator._debounce_timer.isSingleShot()
        assert validator._debounce_delay == 300
        assert validator._fields == {}
        assert validator._external_sources == {}

    def test_initialization_with_custom_debounce(self):
        """Test initialization with custom debounce delay."""
        validator = InputValidator(debounce_delay=500)
        assert validator._debounce_delay == 500

    def test_signals_exist(self):
        """Test that required signals exist."""
        validator = InputValidator()
        assert hasattr(validator, "validationChanged")
        assert hasattr(validator, "fieldValidationChanged")


class TestFieldRegistration:
    """Test field registration functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = InputValidator()
        self.line_edit = QLineEdit()

    def test_register_field_with_qvalidator(self, mock_validator):
        """Test registering field with QValidator."""
        self.validator.register_field("test_field", self.line_edit, mock_validator)

        assert "test_field" in self.validator._fields
        field_info = self.validator._fields["test_field"]
        assert field_info["widget"] is self.line_edit
        assert isinstance(field_info["validator"], FieldValidator)

    def test_register_field_with_callable(self, mock_callable_validator):
        """Test registering field with callable validator."""
        self.validator.register_field("test_field", self.line_edit, mock_callable_validator)

        assert "test_field" in self.validator._fields
        field_info = self.validator._fields["test_field"]
        assert field_info["widget"] is self.line_edit
        assert isinstance(field_info["validator"], FieldValidator)

    def test_register_field_connects_signal(self, mock_validator):
        """Test that registering field connects textChanged signal."""
        with patch.object(self.line_edit, "textChanged") as mock_signal:
            self.validator.register_field("test_field", self.line_edit, mock_validator)
            mock_signal.connect.assert_called_once()

    def test_register_field_duplicate_name(self, mock_validator):
        """Test registering field with duplicate name."""
        self.validator.register_field("test_field", self.line_edit, mock_validator)

        line_edit2 = QLineEdit()
        self.validator.register_field("test_field", line_edit2, mock_validator)

        # Should replace the previous registration
        field_info = self.validator._fields["test_field"]
        assert field_info["widget"] is line_edit2

    def test_unregister_field(self, mock_validator):
        """Test unregistering field."""
        self.validator.register_field("test_field", self.line_edit, mock_validator)
        assert "test_field" in self.validator._fields

        self.validator.unregister_field("test_field")
        assert "test_field" not in self.validator._fields

    def test_unregister_nonexistent_field(self):
        """Test unregistering non-existent field."""
        # Should not raise exception
        self.validator.unregister_field("nonexistent_field")

    def test_register_field_with_error_style(self, mock_validator):
        """Test registering field with custom error style."""
        error_style = "border: 2px solid red;"
        self.validator.register_field("test_field", self.line_edit, mock_validator, error_style=error_style)

        field_info = self.validator._fields["test_field"]
        assert field_info["error_style"] == error_style

    def test_register_field_default_error_style(self, mock_validator):
        """Test registering field with default error style."""
        self.validator.register_field("test_field", self.line_edit, mock_validator)

        field_info = self.validator._fields["test_field"]
        assert "border: 2px solid red" in field_info["error_style"]


class TestValidationExecution:
    """Test validation execution."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = InputValidator()
        self.line_edit = QLineEdit()

    def test_validate_field_valid(self, mock_validator):
        """Test validating field with valid input."""
        self.validator.register_field("test_field", self.line_edit, mock_validator)
        self.line_edit.setText("valid_input")

        result = self.validator.validate_field("test_field")
        assert result is True

    def test_validate_field_invalid(self, mock_invalid_validator):
        """Test validating field with invalid input."""
        self.validator.register_field("test_field", self.line_edit, mock_invalid_validator)
        self.line_edit.setText("invalid_input")

        result = self.validator.validate_field("test_field")
        assert result is False

    def test_validate_field_nonexistent(self):
        """Test validating non-existent field."""
        result = self.validator.validate_field("nonexistent_field")
        assert result is True  # Non-existent fields are considered valid

    def test_validate_all_fields_all_valid(self, mock_validator):
        """Test validating all fields when all are valid."""
        line_edit1 = QLineEdit()
        line_edit2 = QLineEdit()

        self.validator.register_field("field1", line_edit1, mock_validator)
        self.validator.register_field("field2", line_edit2, mock_validator)

        line_edit1.setText("valid1")
        line_edit2.setText("valid2")

        result = self.validator.validate_all_fields()
        assert result is True

    def test_validate_all_fields_some_invalid(self, mock_validator, mock_invalid_validator):
        """Test validating all fields when some are invalid."""
        line_edit1 = QLineEdit()
        line_edit2 = QLineEdit()

        self.validator.register_field("field1", line_edit1, mock_validator)
        self.validator.register_field("field2", line_edit2, mock_invalid_validator)

        line_edit1.setText("valid")
        line_edit2.setText("invalid")

        result = self.validator.validate_all_fields()
        assert result is False

    def test_validate_all_fields_empty(self):
        """Test validating all fields when no fields registered."""
        result = self.validator.validate_all_fields()
        assert result is True

    def test_debounced_validation_triggered(self, mock_validator):
        """Test that debounced validation is triggered on text change."""
        self.validator.register_field("test_field", self.line_edit, mock_validator)

        with patch.object(self.validator._debounce_timer, "start") as mock_start:
            self.line_edit.setText("new_text")
            mock_start.assert_called_once_with(300)

    def test_debounced_validation_execution(self, mock_validator):
        """Test debounced validation execution."""
        self.validator.register_field("test_field", self.line_edit, mock_validator)

        with patch.object(self.validator, "_perform_validation") as mock_perform:
            self.validator._on_debounce_timeout()
            mock_perform.assert_called_once()

    def test_immediate_validation(self, mock_validator):
        """Test immediate validation without debounce."""
        self.validator.register_field("test_field", self.line_edit, mock_validator)
        self.line_edit.setText("test_text")

        with patch.object(self.validator, "_perform_validation") as mock_perform:
            self.validator.validate_immediately()
            mock_perform.assert_called_once()

    def test_get_field_error_message(self, mock_invalid_callable_validator):
        """Test getting error message for specific field."""
        self.validator.register_field("test_field", self.line_edit, mock_invalid_callable_validator)
        self.line_edit.setText("invalid")

        self.validator.validate_field("test_field")
        error_msg = self.validator.get_field_error_message("test_field")
        assert error_msg == "Invalid input"

    def test_get_field_error_message_valid_field(self, mock_validator):
        """Test getting error message for valid field."""
        self.validator.register_field("test_field", self.line_edit, mock_validator)
        self.line_edit.setText("valid")

        self.validator.validate_field("test_field")
        error_msg = self.validator.get_field_error_message("test_field")
        assert error_msg == ""

    def test_get_field_error_message_nonexistent(self):
        """Test getting error message for non-existent field."""
        error_msg = self.validator.get_field_error_message("nonexistent")
        assert error_msg == ""
