"""
Tests for error translation functionality.
"""

from pathlib import Path
from unittest.mock import patch

from core.error_translation import (
    ErrorTranslator,
    UserFriendlyError,
    format_error_for_display,
    log_error_details,
    translate_error,
)
from core.validation import ValidationError


class TestUserFriendlyError:
    """Test UserFriendlyError dataclass."""

    def test_user_friendly_error_creation(self):
        """Test creating UserFriendlyError with all fields."""
        error = UserFriendlyError(
            code="TEST_ERROR",
            title="Test Error",
            message="This is a test error",
            details="Additional details",
            remediation="Try this fix",
            help_url="https://example.com/help",
            field="test_field",
        )

        assert error.code == "TEST_ERROR"
        assert error.title == "Test Error"
        assert error.message == "This is a test error"
        assert error.details == "Additional details"
        assert error.remediation == "Try this fix"
        assert error.help_url == "https://example.com/help"
        assert error.field == "test_field"

    def test_user_friendly_error_to_dict(self):
        """Test converting UserFriendlyError to dictionary."""
        error = UserFriendlyError(
            code="TEST_ERROR",
            title="Test Error",
            message="This is a test error",
            remediation="Try this fix",
        )

        result = error.to_dict()

        assert result["code"] == "TEST_ERROR"
        assert result["title"] == "Test Error"
        assert result["message"] == "This is a test error"
        assert result["remediation"] == "Try this fix"
        assert result["details"] is None
        assert result["help_url"] is None
        assert result["field"] is None


class TestErrorTranslator:
    """Test ErrorTranslator functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.translator = ErrorTranslator()

    def test_translate_validation_error_required(self):
        """Test translating a required field validation error."""
        validation_error = ValidationError(field="pdf", code="required", message="PDF file path is required", value=None)

        result = self.translator.translate_exception(validation_error)

        assert result.code == "VALIDATION_REQUIRED"
        assert result.title == "Required Field Missing"
        assert "pdf field is required" in result.message
        assert result.field == "pdf"
        assert result.help_url is not None

    def test_translate_validation_error_file_not_found(self):
        """Test translating a file not found validation error."""
        validation_error = ValidationError(
            field="pdf",
            code="file_not_found",
            message="PDF file does not exist: /path/to/file.pdf",
            value="/path/to/file.pdf",
        )

        result = self.translator.translate_exception(validation_error)

        assert result.code == "VALIDATION_FILE_NOT_FOUND"
        assert result.title == "File Not Found"
        assert "file could not be found" in result.message
        assert result.field == "pdf"

    def test_translate_validation_error_unknown_code(self):
        """Test translating a validation error with unknown code."""
        validation_error = ValidationError(
            field="test_field", code="unknown_code", message="Unknown validation error", value="test_value"
        )

        result = self.translator.translate_exception(validation_error)

        assert result.code == "VALIDATION_UNKNOWN_CODE"
        assert result.title == "Validation Error"
        assert result.message == "Unknown validation error"
        assert result.field == "test_field"

    def test_translate_file_not_found_error(self):
        """Test translating FileNotFoundError."""
        error = FileNotFoundError("No such file or directory: '/path/to/file.pdf'")

        result = self.translator.translate_exception(error)

        assert result.code.startswith("FILE_SYSTEM_")
        assert result.title == "File Not Found"
        assert "file could not be found" in result.message
        assert result.remediation is not None

    def test_translate_permission_error(self):
        """Test translating PermissionError."""
        error = PermissionError("Permission denied: '/restricted/path'")

        result = self.translator.translate_exception(error)

        assert result.code.startswith("FILE_SYSTEM_")
        assert result.title == "Permission Denied"
        assert "access" in result.message.lower()
        assert "permission" in result.remediation.lower()

    def test_translate_memory_error(self):
        """Test translating MemoryError."""
        error = MemoryError("Out of memory")

        result = self.translator.translate_exception(error)

        assert result.code.startswith("CONVERSION_")
        assert result.title == "Memory Error"
        assert "memory" in result.message.lower()
        assert "fewer workers" in result.remediation.lower()

    def test_translate_import_error_tesseract(self):
        """Test translating ImportError for Tesseract."""
        error = ImportError("No module named 'tesseract'")

        result = self.translator.translate_exception(error)

        assert result.code.startswith("DEPENDENCY_")
        assert result.title == "OCR Dependency Missing"
        assert "tesseract" in result.message.lower()
        assert "install tesseract" in result.remediation.lower()

    def test_translate_unknown_error(self):
        """Test translating an unknown error type."""
        error = RuntimeError("Some unexpected error")

        result = self.translator.translate_exception(error)

        assert result.code == "UNKNOWN_ERROR"
        assert result.title == "Unexpected Error"
        assert "unexpected error" in result.message.lower()
        assert result.details is not None
        assert result.help_url is not None

    def test_sanitize_paths_home_directory(self):
        """Test path sanitization for home directory."""
        home_path = str(Path.home())
        text = f"Error processing file: {home_path}/documents/test.pdf"

        result = self.translator._sanitize_paths(text)

        assert home_path not in result
        assert "~/documents/test.pdf" in result

    def test_sanitize_paths_temp_directory(self):
        """Test path sanitization for temp directory."""
        import tempfile

        temp_dir = tempfile.gettempdir()
        text = f"Error in temp file: {temp_dir}/temp_file.pdf"

        result = self.translator._sanitize_paths(text)

        assert temp_dir not in result
        assert "<temp>/temp_file.pdf" in result

    def test_sanitize_paths_long_paths(self):
        """Test path sanitization for very long paths."""
        text = "Error: /very/long/path/with/many/segments/file.pdf"

        result = self.translator._sanitize_paths(text)

        assert ".../file.pdf" in result
        assert "/very/long/path" not in result

    def test_sanitize_paths_empty_text(self):
        """Test path sanitization with empty text."""
        result = self.translator._sanitize_paths("")
        assert result == ""

        result = self.translator._sanitize_paths(None)
        assert result is None

    def test_matches_pattern_type(self):
        """Test pattern matching by exception type."""
        error = FileNotFoundError("Test error")
        pattern_info = {
            "type_patterns": ["FileNotFoundError"],
            "message_patterns": [],
        }

        result = self.translator._matches_pattern(error, str(error), type(error).__name__, pattern_info)

        assert result is True

    def test_matches_pattern_message(self):
        """Test pattern matching by message content."""
        error = RuntimeError("PDF file is corrupted")
        pattern_info = {
            "type_patterns": [],
            "message_patterns": [r".*corrupt.*"],
        }

        result = self.translator._matches_pattern(error, str(error), type(error).__name__, pattern_info)

        assert result is True

    def test_matches_pattern_no_match(self):
        """Test pattern matching with no match."""
        error = ValueError("Some other error")
        pattern_info = {
            "type_patterns": ["FileNotFoundError"],
            "message_patterns": [r".*corrupt.*pdf.*"],
        }

        result = self.translator._matches_pattern(error, str(error), type(error).__name__, pattern_info)

        assert result is False


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_translate_error_function(self):
        """Test the translate_error convenience function."""
        error = ValueError("Test error")

        result = translate_error(error)

        assert isinstance(result, UserFriendlyError)
        assert result.code == "UNKNOWN_ERROR"
        assert result.title == "Unexpected Error"

    def test_translate_error_with_context(self):
        """Test translate_error with context."""
        error = FileNotFoundError("File not found")
        context = {"file_path": "/test/file.pdf"}

        result = translate_error(error, context)

        assert isinstance(result, UserFriendlyError)
        assert result.code.startswith("FILE_SYSTEM_")

    def test_format_error_for_display_basic(self):
        """Test formatting error for display with basic info."""
        error = UserFriendlyError(
            code="TEST_ERROR",
            title="Test Error",
            message="This is a test error",
        )

        result = format_error_for_display(error)

        assert "This is a test error" in result
        assert "Suggestion:" not in result
        assert "For more help:" not in result

    def test_format_error_for_display_full(self):
        """Test formatting error for display with all info."""
        error = UserFriendlyError(
            code="TEST_ERROR",
            title="Test Error",
            message="This is a test error",
            remediation="Try this fix",
            help_url="https://example.com/help",
        )

        result = format_error_for_display(error)

        assert "This is a test error" in result
        assert "Suggestion: Try this fix" in result
        assert "For more help, visit: https://example.com/help" in result

    @patch("core.error_translation.logger")
    def test_log_error_details(self, mock_logger):
        """Test logging error details."""
        error = UserFriendlyError(
            code="TEST_ERROR",
            title="Test Error",
            message="This is a test error",
            field="test_field",
            details="Additional details",
        )
        original_exception = ValueError("Original error")

        log_error_details(error, original_exception)

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args

        # Check the main message
        assert "TEST_ERROR" in call_args[0][0]
        assert "Test Error" in call_args[0][0]

        # Check the extra data
        extra = call_args[1]["extra"]
        assert extra["error_code"] == "TEST_ERROR"
        assert extra["error_title"] == "Test Error"
        assert extra["error_field"] == "test_field"
        assert extra["error_details"] == "Additional details"

        # Check exception info
        assert call_args[1]["exc_info"] == original_exception

    @patch("core.error_translation.logger")
    def test_log_error_details_no_exception(self, mock_logger):
        """Test logging error details without original exception."""
        error = UserFriendlyError(
            code="TEST_ERROR",
            title="Test Error",
            message="This is a test error",
        )

        log_error_details(error)

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert call_args[1]["exc_info"] is None


class TestErrorPatterns:
    """Test specific error pattern matching."""

    def setup_method(self):
        """Set up test fixtures."""
        self.translator = ErrorTranslator()

    def test_pdf_processing_error_pattern(self):
        """Test PDF processing error pattern matching."""

        # Simulate a PDF processing error
        class MockPDFError(Exception):
            pass

        error = MockPDFError("Corrupt PDF file detected")

        # This should match the PDF processing pattern
        result = self.translator.translate_exception(error)

        # Should match the PDF processing pattern based on message content
        assert result.code.startswith("PDF_PROCESSING_")
        assert result.title == "PDF Processing Error"

    def test_disk_space_error_pattern(self):
        """Test disk space error pattern matching."""
        error = OSError("No space left on device")

        result = self.translator.translate_exception(error)

        assert result.code.startswith("FILE_SYSTEM_")
        assert result.title == "Disk Space Error"
        assert "disk space" in result.message.lower()

    def test_network_error_pattern(self):
        """Test network error pattern matching."""
        from urllib.error import URLError

        error = URLError("Connection timeout")

        result = self.translator.translate_exception(error)

        assert result.code.startswith("NETWORK_")
        assert result.title == "Network Error"
        assert "network error" in result.message.lower()
