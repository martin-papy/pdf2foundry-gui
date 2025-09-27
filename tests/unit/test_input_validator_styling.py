"""
Tests for InputValidator styling and UI feedback functionality.
"""

from unittest.mock import patch

from PySide6.QtWidgets import QLineEdit

from core.errors import ValidationError
from gui.validation.input_validator import InputValidator


class TestFieldStyling:
    """Test field styling functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = InputValidator()
        self.line_edit = QLineEdit()

    def test_apply_error_style(self, mock_invalid_validator):
        """Test applying error style to invalid field."""
        error_style = "border: 2px solid red;"
        self.validator.register_field("test_field", self.line_edit, mock_invalid_validator, error_style=error_style)
        self.line_edit.setText("invalid")

        self.validator.validate_field("test_field")

        # Check that error style was applied
        current_style = self.line_edit.styleSheet()
        assert "border: 2px solid red" in current_style

    def test_remove_error_style(self, mock_validator):
        """Test removing error style from valid field."""
        self.validator.register_field("test_field", self.line_edit, mock_validator)

        # First apply error style
        self.line_edit.setStyleSheet("border: 2px solid red;")

        # Then validate with valid input
        self.line_edit.setText("valid")
        self.validator.validate_field("test_field")

        # Error style should be removed
        current_style = self.line_edit.styleSheet()
        assert "border: 2px solid red" not in current_style

    def test_preserve_existing_style(self, mock_validator):
        """Test that existing styles are preserved when removing error style."""
        existing_style = "background-color: lightblue; font-size: 12px;"
        error_style = "border: 2px solid red;"

        self.validator.register_field("test_field", self.line_edit, mock_validator, error_style=error_style)

        # Set existing style
        self.line_edit.setStyleSheet(existing_style)

        # Store original style
        field_info = self.validator._fields["test_field"]
        field_info["original_style"] = existing_style

        # Apply error style
        self.line_edit.setText("invalid")
        with patch.object(self.validator._fields["test_field"]["validator"], "validate", return_value=False):
            self.validator.validate_field("test_field")

        # Then validate with valid input
        with patch.object(self.validator._fields["test_field"]["validator"], "validate", return_value=True):
            self.validator.validate_field("test_field")

        # Original style should be restored
        current_style = self.line_edit.styleSheet()
        assert "background-color: lightblue" in current_style
        assert "font-size: 12px" in current_style
        assert "border: 2px solid red" not in current_style

    def test_custom_error_style(self, mock_invalid_validator):
        """Test custom error style application."""
        custom_error_style = "border: 3px dashed orange; background-color: yellow;"
        self.validator.register_field("test_field", self.line_edit, mock_invalid_validator, error_style=custom_error_style)

        self.line_edit.setText("invalid")
        self.validator.validate_field("test_field")

        current_style = self.line_edit.styleSheet()
        assert "border: 3px dashed orange" in current_style
        assert "background-color: yellow" in current_style

    def test_style_application_multiple_fields(self, mock_validator, mock_invalid_validator):
        """Test style application across multiple fields."""
        line_edit1 = QLineEdit()
        line_edit2 = QLineEdit()

        self.validator.register_field("field1", line_edit1, mock_validator)
        self.validator.register_field("field2", line_edit2, mock_invalid_validator)

        line_edit1.setText("valid")
        line_edit2.setText("invalid")

        self.validator.validate_all_fields()

        # Field1 should not have error style
        style1 = line_edit1.styleSheet()
        assert "border: 2px solid red" not in style1

        # Field2 should have error style
        style2 = line_edit2.styleSheet()
        assert "border: 2px solid red" in style2

    def test_style_update_on_text_change(self, mock_validator, mock_invalid_validator):
        """Test that style updates when text changes."""
        # Start with invalid validator
        self.validator.register_field("test_field", self.line_edit, mock_invalid_validator)
        self.line_edit.setText("invalid")

        # Trigger validation
        self.validator._on_text_changed("test_field")
        self.validator._on_debounce_timeout()

        # Should have error style
        style = self.line_edit.styleSheet()
        assert "border: 2px solid red" in style

        # Change to valid validator and update text
        field_info = self.validator._fields["test_field"]
        field_info["validator"] = self.validator._create_field_validator(mock_validator)

        self.line_edit.setText("valid")
        self.validator._on_text_changed("test_field")
        self.validator._on_debounce_timeout()

        # Error style should be removed
        style = self.line_edit.styleSheet()
        assert "border: 2px solid red" not in style

    def test_no_style_change_when_validation_unchanged(self, mock_validator):
        """Test that style doesn't change when validation result is unchanged."""
        self.validator.register_field("test_field", self.line_edit, mock_validator)

        # Set initial style
        initial_style = "background-color: lightgray;"
        self.line_edit.setStyleSheet(initial_style)

        # Validate twice with same result
        self.line_edit.setText("valid")
        self.validator.validate_field("test_field")

        style_after_first = self.line_edit.styleSheet()

        self.validator.validate_field("test_field")
        style_after_second = self.line_edit.styleSheet()

        assert style_after_first == style_after_second

    def test_style_restoration_after_unregister(self, mock_invalid_validator):
        """Test that style is restored when field is unregistered."""
        original_style = "background-color: white;"
        self.line_edit.setStyleSheet(original_style)

        self.validator.register_field("test_field", self.line_edit, mock_invalid_validator)

        # Apply error style
        self.line_edit.setText("invalid")
        self.validator.validate_field("test_field")

        # Unregister field
        self.validator.unregister_field("test_field")

        # Original style should be restored
        current_style = self.line_edit.styleSheet()
        assert current_style == original_style


class TestValidatorErrorMessages:
    """Test validator error message handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = InputValidator()
        self.line_edit = QLineEdit()

    def test_qvalidator_error_message(self, mock_invalid_validator):
        """Test error message from QValidator."""
        self.validator.register_field("test_field", self.line_edit, mock_invalid_validator)
        self.line_edit.setText("invalid")

        self.validator.validate_field("test_field")
        error_msg = self.validator.get_field_error_message("test_field")

        assert "Invalid input" in error_msg

    def test_callable_validator_error_message(self, mock_invalid_callable_validator):
        """Test error message from callable validator."""
        self.validator.register_field("test_field", self.line_edit, mock_invalid_callable_validator)
        self.line_edit.setText("invalid")

        self.validator.validate_field("test_field")
        error_msg = self.validator.get_field_error_message("test_field")

        assert error_msg == "Invalid input"

    def test_custom_error_message_callable(self):
        """Test custom error message from callable validator."""

        def custom_validator(value):
            from core.errors import ValidationError

            raise ValidationError("test_field", "CUSTOM_ERROR", "This is a custom error message", value)

        self.validator.register_field("test_field", self.line_edit, custom_validator)
        self.line_edit.setText("invalid")

        self.validator.validate_field("test_field")
        error_msg = self.validator.get_field_error_message("test_field")

        assert error_msg == "This is a custom error message"

    def test_error_message_cleared_on_valid(self, mock_validator):
        """Test that error message is cleared when field becomes valid."""

        # Start with invalid validator to set error message
        def invalid_validator(x):
            raise ValidationError("test_field", "INVALID", "Error message", x)

        self.validator.register_field("test_field", self.line_edit, invalid_validator)
        self.line_edit.setText("invalid")
        self.validator.validate_field("test_field")

        # Should have error message
        error_msg = self.validator.get_field_error_message("test_field")
        assert error_msg == "Error message"

        # Change to valid validator
        field_info = self.validator._fields["test_field"]
        field_info["validator"] = self.validator._create_field_validator(mock_validator)

        self.line_edit.setText("valid")
        self.validator.validate_field("test_field")

        # Error message should be cleared
        error_msg = self.validator.get_field_error_message("test_field")
        assert error_msg == ""

    def test_multiple_field_error_messages(self):
        """Test error messages for multiple fields."""
        line_edit1 = QLineEdit()
        line_edit2 = QLineEdit()

        def validator1(value):
            from core.errors import ValidationError

            raise ValidationError("field1", "ERROR1", "Error in field 1", value)

        def validator2(value):
            from core.errors import ValidationError

            raise ValidationError("field2", "ERROR2", "Error in field 2", value)

        self.validator.register_field("field1", line_edit1, validator1)
        self.validator.register_field("field2", line_edit2, validator2)

        line_edit1.setText("invalid1")
        line_edit2.setText("invalid2")

        self.validator.validate_all_fields()

        error_msg1 = self.validator.get_field_error_message("field1")
        error_msg2 = self.validator.get_field_error_message("field2")

        assert error_msg1 == "Error in field 1"
        assert error_msg2 == "Error in field 2"

    def test_error_message_persistence(self, mock_invalid_callable_validator):
        """Test that error message persists until field is revalidated."""
        self.validator.register_field("test_field", self.line_edit, mock_invalid_callable_validator)
        self.line_edit.setText("invalid")

        self.validator.validate_field("test_field")
        error_msg1 = self.validator.get_field_error_message("test_field")

        # Get error message again without revalidating
        error_msg2 = self.validator.get_field_error_message("test_field")

        assert error_msg1 == error_msg2
        assert error_msg1 == "Invalid input"
