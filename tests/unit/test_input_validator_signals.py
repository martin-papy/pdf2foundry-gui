"""
Tests for InputValidator signal handling and external validation sources.
"""

from unittest.mock import Mock

from PySide6.QtWidgets import QLineEdit

from gui.validation.input_validator import InputValidator


class TestExternalSourceRegistration:
    """Test external validation source registration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = InputValidator()

    def test_register_external_source(self, mock_external_source):
        """Test registering external validation source."""
        self.validator.register_external_source("external1", mock_external_source)

        assert "external1" in self.validator._external_sources
        assert self.validator._external_sources["external1"] is mock_external_source

    def test_register_multiple_external_sources(self, mock_external_source):
        """Test registering multiple external validation sources."""
        source2 = Mock()
        source2.is_valid = True
        source2.error_message = ""

        self.validator.register_external_source("external1", mock_external_source)
        self.validator.register_external_source("external2", source2)

        assert len(self.validator._external_sources) == 2
        assert "external1" in self.validator._external_sources
        assert "external2" in self.validator._external_sources

    def test_unregister_external_source(self, mock_external_source):
        """Test unregistering external validation source."""
        self.validator.register_external_source("external1", mock_external_source)
        assert "external1" in self.validator._external_sources

        self.validator.unregister_external_source("external1")
        assert "external1" not in self.validator._external_sources

    def test_unregister_nonexistent_external_source(self):
        """Test unregistering non-existent external source."""
        # Should not raise exception
        self.validator.unregister_external_source("nonexistent")


class TestExternalValidityHandling:
    """Test external validity handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = InputValidator()

    def test_check_external_validity_all_valid(self, mock_external_source):
        """Test checking external validity when all sources are valid."""
        source2 = Mock()
        source2.is_valid = True
        source2.error_message = ""

        self.validator.register_external_source("external1", mock_external_source)
        self.validator.register_external_source("external2", source2)

        result = self.validator.check_external_validity()
        assert result is True

    def test_check_external_validity_some_invalid(self, mock_external_source):
        """Test checking external validity when some sources are invalid."""
        source2 = Mock()
        source2.is_valid = False
        source2.error_message = "External error"

        self.validator.register_external_source("external1", mock_external_source)
        self.validator.register_external_source("external2", source2)

        result = self.validator.check_external_validity()
        assert result is False

    def test_check_external_validity_no_sources(self):
        """Test checking external validity when no sources registered."""
        result = self.validator.check_external_validity()
        assert result is True

    def test_get_external_error_messages(self):
        """Test getting external error messages."""
        source1 = Mock()
        source1.is_valid = False
        source1.error_message = "Error from source 1"

        source2 = Mock()
        source2.is_valid = True
        source2.error_message = ""

        source3 = Mock()
        source3.is_valid = False
        source3.error_message = "Error from source 3"

        self.validator.register_external_source("external1", source1)
        self.validator.register_external_source("external2", source2)
        self.validator.register_external_source("external3", source3)

        error_messages = self.validator.get_external_error_messages()

        assert len(error_messages) == 2
        assert "Error from source 1" in error_messages
        assert "Error from source 3" in error_messages
        assert "Error from source 2" not in error_messages  # Valid source


class TestOverallValidityChecking:
    """Test overall validity checking combining fields and external sources."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = InputValidator()
        self.line_edit = QLineEdit()

    def test_is_valid_all_valid(self, mock_validator, mock_external_source):
        """Test is_valid when all fields and external sources are valid."""
        self.validator.register_field("test_field", self.line_edit, mock_validator)
        self.validator.register_external_source("external1", mock_external_source)

        self.line_edit.setText("valid")

        result = self.validator.is_valid()
        assert result is True

    def test_is_valid_field_invalid(self, mock_invalid_validator, mock_external_source):
        """Test is_valid when field is invalid."""
        self.validator.register_field("test_field", self.line_edit, mock_invalid_validator)
        self.validator.register_external_source("external1", mock_external_source)

        self.line_edit.setText("invalid")

        result = self.validator.is_valid()
        assert result is False

    def test_is_valid_external_invalid(self, mock_validator):
        """Test is_valid when external source is invalid."""
        external_source = Mock()
        external_source.is_valid = False
        external_source.error_message = "External error"

        self.validator.register_field("test_field", self.line_edit, mock_validator)
        self.validator.register_external_source("external1", external_source)

        self.line_edit.setText("valid")

        result = self.validator.is_valid()
        assert result is False

    def test_is_valid_no_fields_or_sources(self):
        """Test is_valid when no fields or external sources registered."""
        result = self.validator.is_valid()
        assert result is True


class TestSignalEmission:
    """Test signal emission functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = InputValidator()
        self.line_edit = QLineEdit()

    def test_validation_changed_signal_emitted(self, mock_validator):
        """Test that validationChanged signal is emitted."""
        signal_emitted = False
        received_is_valid = None

        def on_validation_changed(is_valid):
            nonlocal signal_emitted, received_is_valid
            signal_emitted = True
            received_is_valid = is_valid

        self.validator.validationChanged.connect(on_validation_changed)
        self.validator.register_field("test_field", self.line_edit, mock_validator)

        self.line_edit.setText("valid")
        self.validator._perform_validation()

        assert signal_emitted
        assert received_is_valid is True

    def test_field_validation_changed_signal_emitted(self, mock_validator):
        """Test that fieldValidationChanged signal is emitted."""
        signal_emitted = False
        received_field_name = None
        received_is_valid = None
        received_error_message = None

        def on_field_validation_changed(field_name, is_valid, error_message):
            nonlocal signal_emitted, received_field_name, received_is_valid, received_error_message
            signal_emitted = True
            received_field_name = field_name
            received_is_valid = is_valid
            received_error_message = error_message

        self.validator.fieldValidationChanged.connect(on_field_validation_changed)
        self.validator.register_field("test_field", self.line_edit, mock_validator)

        self.line_edit.setText("valid")
        self.validator._perform_validation()

        assert signal_emitted
        assert received_field_name == "test_field"
        assert received_is_valid is True
        assert received_error_message == ""

    def test_signal_emission_on_validity_change(self, mock_validator, mock_invalid_validator):
        """Test signal emission when validity changes."""
        signals_emitted = []

        def on_validation_changed(is_valid):
            signals_emitted.append(is_valid)

        self.validator.validationChanged.connect(on_validation_changed)
        self.validator.register_field("test_field", self.line_edit, mock_validator)

        # Start with valid
        self.line_edit.setText("valid")
        self.validator._perform_validation()

        # Change to invalid
        field_info = self.validator._fields["test_field"]
        field_info["validator"] = self.validator._create_field_validator(mock_invalid_validator)
        self.line_edit.setText("invalid")
        self.validator._perform_validation()

        # Should have emitted twice
        assert len(signals_emitted) == 2
        assert signals_emitted[0] is True
        assert signals_emitted[1] is False

    def test_no_signal_emission_when_validity_unchanged(self, mock_validator):
        """Test that signals are not emitted when validity doesn't change."""
        signals_emitted = []

        def on_validation_changed(is_valid):
            signals_emitted.append(is_valid)

        self.validator.validationChanged.connect(on_validation_changed)
        self.validator.register_field("test_field", self.line_edit, mock_validator)

        # Validate twice with same result
        self.line_edit.setText("valid")
        self.validator._perform_validation()
        self.validator._perform_validation()

        # Should only emit once
        assert len(signals_emitted) == 1
        assert signals_emitted[0] is True

    def test_field_signal_emission_multiple_fields(self, mock_validator, mock_invalid_validator):
        """Test field signal emission for multiple fields."""
        field_signals = []

        def on_field_validation_changed(field_name, is_valid, error_message):
            field_signals.append((field_name, is_valid, error_message))

        self.validator.fieldValidationChanged.connect(on_field_validation_changed)

        line_edit1 = QLineEdit()
        line_edit2 = QLineEdit()

        self.validator.register_field("field1", line_edit1, mock_validator)
        self.validator.register_field("field2", line_edit2, mock_invalid_validator)

        line_edit1.setText("valid")
        line_edit2.setText("invalid")

        self.validator._perform_validation()

        # Should emit signals for both fields
        assert len(field_signals) == 2

        # Find signals by field name
        field1_signal = next((s for s in field_signals if s[0] == "field1"), None)
        field2_signal = next((s for s in field_signals if s[0] == "field2"), None)

        assert field1_signal is not None
        assert field1_signal[1] is True  # valid
        assert field1_signal[2] == ""  # no error

        assert field2_signal is not None
        assert field2_signal[1] is False  # invalid
        assert field2_signal[2] != ""  # has error


class TestPublicInterface:
    """Test public interface methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = InputValidator()
        self.line_edit = QLineEdit()

    def test_clear_all_errors(self, mock_invalid_validator):
        """Test clearing all field errors."""
        line_edit1 = QLineEdit()
        line_edit2 = QLineEdit()

        self.validator.register_field("field1", line_edit1, mock_invalid_validator)
        self.validator.register_field("field2", line_edit2, mock_invalid_validator)

        # Apply error styles
        line_edit1.setText("invalid")
        line_edit2.setText("invalid")
        self.validator.validate_all_fields()

        # Both should have error styles
        assert "border: 2px solid red" in line_edit1.styleSheet()
        assert "border: 2px solid red" in line_edit2.styleSheet()

        # Clear all errors
        self.validator.clear_all_errors()

        # Error styles should be removed
        assert "border: 2px solid red" not in line_edit1.styleSheet()
        assert "border: 2px solid red" not in line_edit2.styleSheet()

    def test_get_all_error_messages(self):
        """Test getting all error messages."""
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

        line_edit1.setText("invalid")
        line_edit2.setText("invalid")

        self.validator.validate_all_fields()

        error_messages = self.validator.get_all_error_messages()

        assert len(error_messages) == 2
        assert "field1" in error_messages
        assert "field2" in error_messages
        assert error_messages["field1"] == "Error in field 1"
        assert error_messages["field2"] == "Error in field 2"

    def test_has_errors(self, mock_validator, mock_invalid_validator):
        """Test has_errors method."""
        line_edit1 = QLineEdit()
        line_edit2 = QLineEdit()

        self.validator.register_field("field1", line_edit1, mock_validator)
        self.validator.register_field("field2", line_edit2, mock_invalid_validator)

        line_edit1.setText("valid")
        line_edit2.setText("invalid")

        self.validator.validate_all_fields()

        assert self.validator.has_errors() is True

        # Fix the invalid field
        field_info = self.validator._fields["field2"]
        field_info["validator"] = self.validator._create_field_validator(mock_validator)
        line_edit2.setText("valid")
        self.validator.validate_all_fields()

        assert self.validator.has_errors() is False

    def test_reset_validation_state(self, mock_invalid_validator):
        """Test resetting validation state."""
        self.validator.register_field("test_field", self.line_edit, mock_invalid_validator)

        # Apply error state
        self.line_edit.setText("invalid")
        self.validator.validate_field("test_field")

        # Should have error
        assert self.validator.has_errors() is True
        assert "border: 2px solid red" in self.line_edit.styleSheet()

        # Reset validation state
        self.validator.reset_validation_state()

        # Error should be cleared
        assert self.validator.has_errors() is False
        assert "border: 2px solid red" not in self.line_edit.styleSheet()
