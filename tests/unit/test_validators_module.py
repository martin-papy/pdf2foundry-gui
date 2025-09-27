"""
Tests for module-specific validators.

Tests cover:
- ModuleIdValidator for Foundry VTT module IDs
- ModuleTitleValidator with length limits
"""

from PySide6.QtGui import QValidator

from gui.validation.validators import ModuleIdValidator, ModuleTitleValidator


class TestModuleIdValidator:
    """Test the ModuleIdValidator for Foundry VTT module IDs."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ModuleIdValidator()

    def test_valid_module_ids(self):
        """Test valid module ID patterns."""
        valid_ids = [
            "my-module",
            "test_module",
            "module123",
            "a-b-c",
            "test-module-v2",
            "my_awesome_module",
            "123-test",
            "a" * 64,  # Maximum length
            "abc",  # Minimum length
        ]

        for module_id in valid_ids:
            state, text, _pos = self.validator.validate(module_id, 0)
            assert state == QValidator.State.Acceptable, f"'{module_id}' should be valid"
            assert text == module_id

    def test_invalid_module_ids(self):
        """Test invalid module ID patterns."""
        invalid_ids = [
            "AB",  # Too short
            "a" * 65,  # Too long
            "My-Module",  # Uppercase letters
            "my module",  # Spaces
            "my.module",  # Dots
            "my@module",  # Special characters
            "my/module",  # Slashes
            "",  # Empty
            "12",  # Only numbers (too short)
            "test-",  # Ending with hyphen
        ]

        for module_id in invalid_ids:
            state, text, pos = self.validator.validate(module_id, 0)
            assert state != QValidator.State.Acceptable, f"'{module_id}' should be invalid"

        # Special case: starting with hyphen should be invalid
        state, _text, _pos = self.validator.validate("-test", 0)
        assert state == QValidator.State.Invalid, "'-test' should be invalid"

    def test_reserved_module_ids(self):
        """Test that reserved module IDs are rejected."""
        reserved_ids = [
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
        ]

        for reserved_id in reserved_ids:
            state, _text, _pos = self.validator.validate(reserved_id, 0)
            assert state == QValidator.State.Invalid, f"'{reserved_id}' should be reserved"

    def test_fixup_functionality(self):
        """Test the fixup method for correcting input."""
        test_cases = [
            ("My Module", "my-module"),
            ("TEST_MODULE", "test_module"),
            ("my..module", "my-module"),
            ("  test  ", "test"),  # Just trim, already 4 chars
            ("a" * 70, "a" * 64),  # Truncate to maximum length
            ("my---module", "my-module"),  # Remove consecutive hyphens
            ("-test-", "test"),  # Remove leading/trailing hyphens
            ("my@#$module", "my-module"),  # Replace invalid chars, then clean up
            ("ab", "ab0"),  # Pad short input to minimum length
        ]

        for input_text, expected in test_cases:
            result = self.validator.fixup(input_text)
            assert result == expected, f"fixup('{input_text}') should be '{expected}', got '{result}'"

    def test_intermediate_states(self):
        """Test intermediate validation states during typing."""
        # These might be intermediate during typing
        intermediate_cases = [
            "a",  # Too short but could be extended
            "ab",  # Too short but could be extended
        ]

        for case in intermediate_cases:
            state, _text, _pos = self.validator.validate(case, 0)
            # Should be intermediate (too short but could be extended)
            assert state == QValidator.State.Intermediate


class TestModuleTitleValidator:
    """Test the ModuleTitleValidator for module titles."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ModuleTitleValidator()

    def test_valid_module_titles(self):
        """Test valid module title patterns."""
        valid_titles = [
            "My Awesome Module",
            "Test Module v2.0",
            "Simple Title",
            "A" * 100,  # Maximum length
            "A",  # Minimum length
            "Module with Numbers 123",
            "Special Characters: - _ ( ) [ ]",
            "Unicode: Café Münü",
        ]

        for title in valid_titles:
            state, text, _pos = self.validator.validate(title, 0)
            assert state == QValidator.State.Acceptable, f"'{title}' should be valid"
            assert text == title

    def test_invalid_module_titles(self):
        """Test invalid module title patterns."""
        invalid_titles = [
            "",  # Empty
            "A" * 101,  # Too long
            "Title with\nnewline",  # Newlines not allowed
            "Title with\ttab",  # Tabs not allowed
            "Title with\rcarriage return",  # Carriage returns not allowed
        ]

        for title in invalid_titles:
            state, _text, _pos = self.validator.validate(title, 0)
            assert state != QValidator.State.Acceptable, f"'{title}' should be invalid"

    def test_fixup_functionality(self):
        """Test the fixup method for correcting input."""
        test_cases = [
            ("  Title with spaces  ", "Title with spaces"),  # Trim whitespace
            ("A" * 105, "A" * 100),  # Truncate to maximum length
            ("Title\nwith\nnewlines", "Title with newlines"),  # Replace newlines
            ("Title\twith\ttabs", "Title with tabs"),  # Replace tabs
            ("Title\rwith\rCR", "Title with CR"),  # Replace carriage returns
            ("", ""),  # Empty remains empty (will be invalid)
        ]

        for input_text, expected in test_cases:
            result = self.validator.fixup(input_text)
            assert result == expected, f"fixup('{input_text}') should be '{expected}', got '{result}'"

    def test_intermediate_states(self):
        """Test intermediate validation states during typing."""
        # Empty string should be intermediate (user might be typing)
        state, _text, _pos = self.validator.validate("", 0)
        assert state == QValidator.State.Intermediate

    def test_whitespace_handling(self):
        """Test handling of various whitespace characters."""
        # Leading/trailing spaces should be acceptable (fixup will clean)
        state, _text, _pos = self.validator.validate("  Valid Title  ", 0)
        assert state == QValidator.State.Acceptable

        # Internal spaces should be fine
        state, _text, _pos = self.validator.validate("Valid Title", 0)
        assert state == QValidator.State.Acceptable
