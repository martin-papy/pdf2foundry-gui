"""
Tests for path and numeric validators.

Tests cover:
- PathWritableValidator for directory validation
- NumericRangeValidator for integer inputs
- DecimalRangeValidator for float inputs
"""

import os
import tempfile
from pathlib import Path

from PySide6.QtCore import QLocale
from PySide6.QtGui import QValidator

from gui.validation.validators import (
    DecimalRangeValidator,
    NumericRangeValidator,
    PathWritableValidator,
)


class TestPathWritableValidator:
    """Test the PathWritableValidator for directory validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = PathWritableValidator()

    def test_valid_writable_directory(self):
        """Test validation of a valid writable directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state, _text, _pos = self.validator.validate(temp_dir, 0)
            assert state == QValidator.State.Acceptable

    def test_empty_path_intermediate(self):
        """Test that empty path is intermediate."""
        state, text, pos = self.validator.validate("", 0)
        assert state == QValidator.State.Intermediate

        state, _text, _pos = self.validator.validate("   ", 0)
        assert state == QValidator.State.Intermediate

    def test_nonexistent_path_intermediate(self):
        """Test that non-existent path is intermediate."""
        nonexistent_path = "/this/path/does/not/exist"
        state, _text, _pos = self.validator.validate(nonexistent_path, 0)
        assert state == QValidator.State.Intermediate

    def test_file_instead_of_directory_invalid(self):
        """Test that a file path (not directory) is invalid."""
        with tempfile.NamedTemporaryFile() as temp_file:
            state, _text, _pos = self.validator.validate(temp_file.name, 0)
            assert state == QValidator.State.Invalid

    def test_non_writable_directory_invalid(self):
        """Test that non-writable directory is invalid."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Make directory non-writable
            os.chmod(temp_dir, 0o444)  # Read-only

            try:
                state, _text, _pos = self.validator.validate(temp_dir, 0)
                assert state == QValidator.State.Invalid
            finally:
                # Restore write permissions for cleanup
                os.chmod(temp_dir, 0o755)

    def test_invalid_path_characters_invalid(self):
        """Test that paths with invalid characters are invalid."""
        if os.name == "nt":  # Windows
            invalid_paths = [
                "C:\\invalid<path",
                "C:\\invalid>path",
                "C:\\invalid|path",
            ]
        else:  # Unix-like
            invalid_paths = [
                "/path/with\x00null",
            ]

        for invalid_path in invalid_paths:
            state, _text, _pos = self.validator.validate(invalid_path, 0)
            assert state == QValidator.State.Invalid

    def test_fixup_normalizes_path(self):
        """Test that fixup normalizes the path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with extra spaces and relative path components
            messy_path = f"  {temp_dir}/../{Path(temp_dir).name}  "

            result = self.validator.fixup(messy_path)

            # Should be normalized (no spaces, resolved)
            assert result.strip() == result
            assert Path(result).is_absolute()

    def test_home_directory_expansion(self):
        """Test that ~ is expanded to home directory."""
        home_path = "~/test"

        result = self.validator.fixup(home_path)

        assert "~" not in result
        assert str(Path.home()) in result


class TestNumericRangeValidator:
    """Test the NumericRangeValidator for integer inputs."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = NumericRangeValidator(1, 100)

    def test_valid_integers_in_range(self):
        """Test valid integers within the specified range."""
        valid_values = ["1", "50", "100", "25"]

        for value in valid_values:
            state, _text, _pos = self.validator.validate(value, 0)
            assert state == QValidator.State.Acceptable, f"'{value}' should be valid"

    def test_integers_out_of_range_invalid(self):
        """Test integers outside the specified range."""
        invalid_values = ["0", "101", "-5", "1000"]

        for value in invalid_values:
            state, _text, _pos = self.validator.validate(value, 0)
            # Out of range values are typically Intermediate, not Invalid
            assert state == QValidator.State.Intermediate, f"'{value}' should be intermediate (out of range)"

    def test_non_integer_values_invalid(self):
        """Test non-integer values."""
        invalid_values = ["abc", "12.5", "1.0", "fifty", ""]

        for value in invalid_values:
            state, _text, _pos = self.validator.validate(value, 0)
            assert state != QValidator.State.Acceptable, f"'{value}' should not be acceptable"

    def test_empty_string_intermediate(self):
        """Test that empty string is intermediate."""
        state, _text, _pos = self.validator.validate("", 0)
        assert state == QValidator.State.Intermediate

    def test_partial_input_intermediate(self):
        """Test that partial valid input is intermediate."""
        # These might be intermediate during typing
        partial_inputs = ["5", "10"]  # Valid but could be part of larger number

        for value in partial_inputs:
            state, _text, _pos = self.validator.validate(value, 0)
            # Should be acceptable since they're complete valid numbers
            assert state == QValidator.State.Acceptable

    def test_range_boundaries(self):
        """Test the exact boundaries of the range."""
        # Test minimum boundary
        state, text, pos = self.validator.validate("1", 0)
        assert state == QValidator.State.Acceptable

        # Test maximum boundary
        state, text, pos = self.validator.validate("100", 0)
        assert state == QValidator.State.Acceptable

        # Test just outside boundaries - these should be Intermediate, not Invalid
        state, text, pos = self.validator.validate("0", 0)
        assert state == QValidator.State.Intermediate

        state, _text, _pos = self.validator.validate("101", 0)
        assert state == QValidator.State.Intermediate


class TestDecimalRangeValidator:
    """Test the DecimalRangeValidator for float inputs."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = DecimalRangeValidator(0.0, 1.0, 2)  # 2 decimal places

    def test_valid_decimals_in_range(self):
        """Test valid decimal values within the specified range."""
        valid_values = ["0.0", "0.5", "1.0", "0.25", "0.75"]

        for value in valid_values:
            state, _text, _pos = self.validator.validate(value, 0)
            assert state == QValidator.State.Acceptable, f"'{value}' should be valid"

    def test_decimals_out_of_range_intermediate(self):
        """Test decimal values outside the specified range."""
        out_of_range_values = ["-0.1", "1.1", "2.0", "-1.0"]

        for value in out_of_range_values:
            state, _text, _pos = self.validator.validate(value, 0)
            # Out of range values should be Intermediate
            assert state == QValidator.State.Intermediate, f"'{value}' should be intermediate (out of range)"

    def test_too_many_decimal_places_intermediate(self):
        """Test values with too many decimal places."""
        too_precise_values = ["0.123", "0.5555", "1.0001"]

        for value in too_precise_values:
            state, _text, _pos = self.validator.validate(value, 0)
            # Too many decimals should be Intermediate (could be rounded)
            assert state == QValidator.State.Intermediate, f"'{value}' should be intermediate (too precise)"

    def test_non_numeric_values_invalid(self):
        """Test non-numeric values."""
        invalid_values = ["abc", "half", "0.5.0", ""]

        for value in invalid_values:
            state, _text, _pos = self.validator.validate(value, 0)
            assert state != QValidator.State.Acceptable, f"'{value}' should not be acceptable"

    def test_empty_string_intermediate(self):
        """Test that empty string is intermediate."""
        state, _text, _pos = self.validator.validate("", 0)
        assert state == QValidator.State.Intermediate

    def test_partial_decimal_intermediate(self):
        """Test partial decimal input during typing."""
        partial_inputs = ["0.", "1.", ".5"]

        for value in partial_inputs:
            state, _text, _pos = self.validator.validate(value, 0)
            # These should be intermediate (incomplete but potentially valid)
            assert state == QValidator.State.Intermediate, f"'{value}' should be intermediate"

    def test_locale_handling(self):
        """Test that validator respects locale settings."""
        # Create validator with German locale (uses comma as decimal separator)
        german_locale = QLocale(QLocale.Language.German)
        validator = DecimalRangeValidator(0.0, 1.0, 2, locale=german_locale)

        # Test German decimal format
        state, _text, _pos = validator.validate("0,5", 0)
        assert state == QValidator.State.Acceptable, "German decimal format should be valid"

    def test_range_boundaries(self):
        """Test the exact boundaries of the range."""
        # Test minimum boundary
        state, _text, _pos = self.validator.validate("0.0", 0)
        assert state == QValidator.State.Acceptable

        # Test maximum boundary
        state, _text, _pos = self.validator.validate("1.0", 0)
        assert state == QValidator.State.Acceptable

        # Test just outside boundaries
        state, _text, _pos = self.validator.validate("-0.01", 0)
        assert state == QValidator.State.Intermediate

        state, _text, _pos = self.validator.validate("1.01", 0)
        assert state == QValidator.State.Intermediate
