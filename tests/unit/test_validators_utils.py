"""
Tests for validator utility functions and integration scenarios.

Tests cover:
- create_validation_error utility function
- Integration scenarios with multiple validators
"""

import tempfile

from PySide6.QtGui import QValidator

from core.errors import ErrorCode, ValidationError
from gui.validation.validators import (
    ModuleIdValidator,
    ModuleTitleValidator,
    NumericRangeValidator,
    PathWritableValidator,
    create_validation_error,
)


class TestCreateValidationError:
    """Test the create_validation_error utility function."""

    def test_basic_validation_error_creation(self):
        """Test basic validation error creation."""
        error = create_validation_error("test_field", "Invalid input", "bad_value")

        assert isinstance(error, ValidationError)
        assert error.field == "test_field"
        assert error.user_message == "Invalid input"
        assert error.context["value"] == "bad_value"
        assert error.code == ErrorCode.INVALID_INPUT

    def test_error_code_detection_required_field(self):
        """Test error code detection for required fields."""
        error = create_validation_error("field", "This field is required")
        assert error.code == ErrorCode.REQUIRED_FIELD_MISSING

    def test_error_code_detection_format_error(self):
        """Test error code detection for format errors."""
        error = create_validation_error("field", "Invalid format provided")
        assert error.code == ErrorCode.INVALID_FORMAT

        error = create_validation_error("field", "Pattern does not match")
        assert error.code == ErrorCode.INVALID_FORMAT

    def test_error_code_detection_range_error(self):
        """Test error code detection for range errors."""
        error = create_validation_error("field", "Value out of range")
        assert error.code == ErrorCode.VALUE_OUT_OF_RANGE

        error = create_validation_error("field", "Length exceeds maximum")
        assert error.code == ErrorCode.VALUE_OUT_OF_RANGE

    def test_error_code_detection_file_not_found(self):
        """Test error code detection for file not found."""
        error = create_validation_error("path", "Path not found")
        assert error.code == ErrorCode.FILE_NOT_FOUND

    def test_error_code_detection_permission_denied(self):
        """Test error code detection for permission errors."""
        error = create_validation_error("path", "Permission denied")
        assert error.code == ErrorCode.PERMISSION_DENIED

        error = create_validation_error("path", "Directory not writable")
        assert error.code == ErrorCode.PERMISSION_DENIED

    def test_technical_message_generation(self):
        """Test that technical message is generated correctly."""
        error = create_validation_error("test_field", "Test error", "test_value")

        expected_technical = "Validation failed for field 'test_field': Test error"
        assert error.technical_message == expected_technical

    def test_no_value_context(self):
        """Test error creation without value context."""
        error = create_validation_error("field", "Error message")

        assert "value" not in error.context
        assert error.context == {"field": "field"}  # Field is always added to context

    def test_case_insensitive_detection(self):
        """Test that error code detection is case insensitive."""
        error = create_validation_error("field", "REQUIRED field missing")
        assert error.code == ErrorCode.REQUIRED_FIELD_MISSING

        error = create_validation_error("field", "Invalid FORMAT")
        assert error.code == ErrorCode.INVALID_FORMAT


class TestValidatorIntegration:
    """Test integration scenarios with multiple validators."""

    def test_module_id_and_title_together(self):
        """Test using module ID and title validators together."""
        id_validator = ModuleIdValidator()
        title_validator = ModuleTitleValidator()

        # Valid combination
        id_state, _, _ = id_validator.validate("my-awesome-module", 0)
        title_state, _, _ = title_validator.validate("My Awesome Module", 0)

        assert id_state == QValidator.State.Acceptable
        assert title_state == QValidator.State.Acceptable

    def test_path_and_numeric_validators(self):
        """Test using path and numeric validators together."""
        path_validator = PathWritableValidator()
        numeric_validator = NumericRangeValidator(1, 10)

        with tempfile.TemporaryDirectory() as temp_dir:
            path_state, _, _ = path_validator.validate(temp_dir, 0)
            numeric_state, _, _ = numeric_validator.validate("5", 0)

            assert path_state == QValidator.State.Acceptable
            assert numeric_state == QValidator.State.Acceptable

    def test_validation_error_consistency(self):
        """Test that validation errors are created consistently."""
        # Test different error types
        errors = [
            create_validation_error("field1", "Required field missing"),
            create_validation_error("field2", "Invalid format"),
            create_validation_error("field3", "Value out of range"),
        ]

        # All should be ValidationError instances
        for error in errors:
            assert isinstance(error, ValidationError)
            assert error.field.startswith("field")
            assert error.technical_message.startswith("Validation failed")

    def test_validator_fixup_integration(self):
        """Test that fixup methods work consistently across validators."""
        id_validator = ModuleIdValidator()
        title_validator = ModuleTitleValidator()

        # Test fixup on related inputs
        messy_id = "  My Awesome Module  "
        messy_title = "  My Awesome Module  "

        fixed_id = id_validator.fixup(messy_id)
        fixed_title = title_validator.fixup(messy_title)

        # ID should be normalized to lowercase with dashes
        assert fixed_id == "my-awesome-module"
        # Title should just be trimmed
        assert fixed_title == "My Awesome Module"

        # Both should validate as acceptable after fixup
        id_state, _, _ = id_validator.validate(fixed_id, 0)
        title_state, _, _ = title_validator.validate(fixed_title, 0)

        assert id_state == QValidator.State.Acceptable
        assert title_state == QValidator.State.Acceptable
