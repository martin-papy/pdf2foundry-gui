"""
Error translation and user-friendly message generation.

This module provides functionality to translate backend exceptions and validation
errors into actionable UI messages with remediation hints.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from .errors import BaseAppError, ErrorType
from .validation import ValidationError

logger = logging.getLogger(__name__)


@dataclass
class UserFriendlyError:
    """
    User-friendly error representation for UI display.

    Contains all information needed to present a helpful error message
    to the user with actionable remediation steps.
    """

    code: str
    title: str
    message: str
    details: str | None = None
    remediation: str | None = None
    help_url: str | None = None
    field: str | None = None  # GUI field that caused the error (if applicable)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "code": self.code,
            "title": self.title,
            "message": self.message,
            "details": self.details,
            "remediation": self.remediation,
            "help_url": self.help_url,
            "field": self.field,
        }


class ErrorTranslator:
    """
    Translates backend exceptions and validation errors into user-friendly messages.

    This class maintains a mapping of known error patterns to user-friendly
    messages with remediation hints and help links.
    """

    # Base help URL for documentation
    HELP_BASE_URL = "https://github.com/your-org/pdf2foundry-gui/wiki"

    # Error code categories
    ERROR_CATEGORIES: ClassVar[dict[str, str]] = {
        "validation": "VALIDATION",
        "file_system": "FILE_SYSTEM",
        "pdf_processing": "PDF_PROCESSING",
        "conversion": "CONVERSION",
        "dependency": "DEPENDENCY",
        "configuration": "CONFIGURATION",
        "network": "NETWORK",
        "unknown": "UNKNOWN",
    }

    def __init__(self) -> None:
        """Initialize the error translator."""
        self._error_patterns = self._build_error_patterns()

    def translate_exception(self, exception: Exception, context: dict[str, Any] | None = None) -> UserFriendlyError:
        """
        Translate an exception into a user-friendly error.

        Args:
            exception: The exception to translate
            context: Optional context information (e.g., file paths, settings)

        Returns:
            UserFriendlyError with translated message and remediation
        """
        context = context or {}

        # Handle ValidationError specifically first (before BaseAppError check)
        if isinstance(exception, ValidationError):
            return self._translate_validation_error(exception, context)

        # Handle new BaseAppError hierarchy
        if isinstance(exception, BaseAppError):
            return self.from_app_error(exception)

        # Try to match against known error patterns
        exception_str = str(exception)
        exception_type = type(exception).__name__

        for pattern_info in self._error_patterns:
            if self._matches_pattern(exception, exception_str, exception_type, pattern_info):
                return self._build_error_from_pattern(exception, pattern_info, context)

        # Fallback for unknown errors
        return self._translate_unknown_error(exception, context)

    def from_app_error(self, app_error: BaseAppError) -> UserFriendlyError:
        """
        Convert a BaseAppError to a UserFriendlyError.

        Args:
            app_error: The BaseAppError to convert

        Returns:
            UserFriendlyError with appropriate UI display information
        """
        # Map ErrorType to category for help URL generation
        type_to_category = {
            ErrorType.FILE: "file_system",
            ErrorType.VALIDATION: "validation",
            ErrorType.CONVERSION: "conversion",
            ErrorType.CONFIG: "configuration",
            ErrorType.SYSTEM: "unknown",  # Default fallback
        }

        category = type_to_category.get(app_error.type, "unknown")
        code = f"{self.ERROR_CATEGORIES[category]}_{app_error.code.value}"

        # Use user_message if available, otherwise technical_message
        message = app_error.user_message or app_error.technical_message or "An error occurred"

        # Generate help URL based on error type
        help_url = f"{self.HELP_BASE_URL}/troubleshooting#{app_error.type.value}-errors"

        # Extract field from context if it's a validation error
        field = app_error.context.get("field") if app_error.context else None

        return UserFriendlyError(
            code=code,
            title=self._generate_title_from_error_type(app_error.type),
            message=self._sanitize_paths(message),
            details=self._sanitize_paths(app_error.technical_message) if app_error.technical_message else None,
            remediation=self._generate_remediation_from_error(app_error),
            help_url=help_url,
            field=field,
        )

    def _generate_title_from_error_type(self, error_type: ErrorType) -> str:
        """Generate a user-friendly title from error type."""
        titles = {
            ErrorType.FILE: "File Error",
            ErrorType.VALIDATION: "Input Error",
            ErrorType.CONVERSION: "Conversion Error",
            ErrorType.CONFIG: "Configuration Error",
            ErrorType.SYSTEM: "System Error",
        }
        return titles.get(error_type, "Error")

    def _generate_remediation_from_error(self, app_error: BaseAppError) -> str | None:
        """Generate remediation suggestions based on error code."""
        remediation_map = {
            "FILE_NOT_FOUND": "Please check that the file exists and try again.",
            "PERMISSION_DENIED": "Please check file permissions or try running as administrator.",
            "INVALID_INPUT": "Please check your input and try again.",
            "OPERATION_CANCELLED": "The operation was cancelled. You can try again if needed.",
            "BACKEND_FAILURE": "Please try again or contact support if the problem persists.",
        }

        return remediation_map.get(app_error.code.value)

    def _translate_validation_error(self, error: ValidationError, context: dict[str, Any]) -> UserFriendlyError:
        """Translate a ValidationError into user-friendly format."""
        # Map validation error codes to user-friendly messages
        validation_messages = {
            "required": {
                "title": "Required Field Missing",
                "message": f"The {error.field} field is required.",
                "remediation": f"Please provide a value for {error.field}.",
            },
            "invalid_format": {
                "title": "Invalid Format",
                "message": f"The {error.field} field has an invalid format.",
                "remediation": "Please check the format and try again.",
            },
            "file_not_found": {
                "title": "File Not Found",
                "message": "The specified file could not be found.",
                "remediation": "Please check that the file exists and try again.",
            },
            "not_readable": {
                "title": "File Access Error",
                "message": "The file cannot be read.",
                "remediation": "Please check file permissions and try again.",
            },
            "not_writable": {
                "title": "Directory Access Error",
                "message": "Cannot write to the specified directory.",
                "remediation": "Please check directory permissions or choose a different location.",
            },
            "out_of_range": {
                "title": "Value Out of Range",
                "message": f"The {error.field} value is outside the allowed range.",
                "remediation": "Please enter a value within the valid range.",
            },
            "invalid_page_number": {
                "title": "Invalid Page Number",
                "message": "Page numbers must be positive integers.",
                "remediation": "Please enter valid page numbers (e.g., 1,3,5-10).",
            },
            "duplicate_pages": {
                "title": "Duplicate Pages",
                "message": "The page list contains duplicate page numbers.",
                "remediation": "Please remove duplicate page numbers from the list.",
            },
        }

        error_info = validation_messages.get(
            error.legacy_code,
            {
                "title": "Validation Error",
                "message": error.message,
                "remediation": "Please correct the input and try again.",
            },
        )

        # Sanitize file paths in the message
        sanitized_message = self._sanitize_paths(error_info["message"])

        return UserFriendlyError(
            code=f"VALIDATION_{error.legacy_code.upper()}",
            title=error_info["title"],
            message=sanitized_message,
            remediation=error_info["remediation"],
            field=error.field,
            help_url=f"{self.HELP_BASE_URL}/validation-errors",
        )

    def _build_error_patterns(self) -> list[dict[str, Any]]:
        """Build the list of error patterns for matching."""
        return [
            # PDF Processing Errors
            {
                "type_patterns": ["PyPDF2.*Error", "PdfReader.*Error", ".*PDF.*Error"],
                "message_patterns": [r".*corrupt.*", r".*invalid.*pdf.*", r".*damaged.*pdf.*"],
                "category": "pdf_processing",
                "title": "PDF Processing Error",
                "message": "The PDF file appears to be corrupted or invalid.",
                "remediation": "Please try with a different PDF file or repair the current one.",
                "help_url": "pdf-processing-errors",
            },
            {
                "type_patterns": ["PermissionError"],
                "message_patterns": [r".*permission.*denied.*"],
                "category": "file_system",
                "title": "Permission Denied",
                "message": "Access to the file or directory was denied.",
                "remediation": "Please check file/directory permissions and try again.",
                "help_url": "permission-errors",
            },
            {
                "type_patterns": ["FileNotFoundError"],
                "message_patterns": [r".*no such file.*", r".*file not found.*"],
                "category": "file_system",
                "title": "File Not Found",
                "message": "The specified file could not be found.",
                "remediation": "Please check the file path and ensure the file exists.",
                "help_url": "file-errors",
            },
            {
                "type_patterns": ["OSError", "IOError"],
                "message_patterns": [r".*disk.*full.*", r".*no space.*"],
                "category": "file_system",
                "title": "Disk Space Error",
                "message": "There is not enough disk space to complete the operation.",
                "remediation": "Please free up disk space or choose a different output location.",
                "help_url": "disk-space-errors",
            },
            {
                "type_patterns": ["ImportError", "ModuleNotFoundError"],
                "message_patterns": [r".*tesseract.*", r".*ocr.*"],
                "category": "dependency",
                "title": "OCR Dependency Missing",
                "message": "Tesseract OCR is required but not installed.",
                "remediation": "Please install Tesseract OCR or disable OCR in settings.",
                "help_url": "ocr-setup",
            },
            {
                "type_patterns": ["ImportError", "ModuleNotFoundError"],
                "message_patterns": [r".*node.*", r".*npm.*", r".*foundry.*cli.*"],
                "category": "dependency",
                "title": "Foundry CLI Missing",
                "message": "Foundry CLI is required for pack compilation but not found.",
                "remediation": "Please install Foundry CLI or disable pack compilation.",
                "help_url": "foundry-cli-setup",
            },
            {
                "type_patterns": ["ConnectionError", "TimeoutError", "URLError"],
                "message_patterns": [r".*network.*", r".*connection.*", r".*timeout.*"],
                "category": "network",
                "title": "Network Error",
                "message": "A network error occurred during processing.",
                "remediation": "Please check your internet connection and try again.",
                "help_url": "network-errors",
            },
            {
                "type_patterns": ["MemoryError"],
                "message_patterns": [r".*memory.*", r".*out of memory.*"],
                "category": "conversion",
                "title": "Memory Error",
                "message": "The system ran out of memory during processing.",
                "remediation": "Please try with fewer workers or a smaller PDF file.",
                "help_url": "memory-errors",
            },
            # Add more patterns as needed
        ]

    def _matches_pattern(
        self, exception: Exception, exception_str: str, exception_type: str, pattern_info: dict[str, Any]
    ) -> bool:
        """Check if an exception matches a pattern."""
        # Check exception type patterns
        type_patterns = pattern_info.get("type_patterns", [])
        for type_pattern in type_patterns:
            if re.match(type_pattern, exception_type, re.IGNORECASE):
                return True

        # Check message patterns
        message_patterns = pattern_info.get("message_patterns", [])
        return any(re.search(message_pattern, exception_str, re.IGNORECASE) for message_pattern in message_patterns)

    def _build_error_from_pattern(
        self, exception: Exception, pattern_info: dict[str, Any], context: dict[str, Any]
    ) -> UserFriendlyError:
        """Build a UserFriendlyError from a matched pattern."""
        category = pattern_info["category"]
        code = f"{self.ERROR_CATEGORIES[category]}_{pattern_info.get('code', 'GENERIC')}"

        # Sanitize paths in the message
        message = self._sanitize_paths(pattern_info["message"])

        help_url = None
        if pattern_info.get("help_url"):
            help_url = f"{self.HELP_BASE_URL}/{pattern_info['help_url']}"

        return UserFriendlyError(
            code=code,
            title=pattern_info["title"],
            message=message,
            details=self._sanitize_paths(str(exception)),
            remediation=pattern_info.get("remediation"),
            help_url=help_url,
        )

    def _translate_unknown_error(self, exception: Exception, context: dict[str, Any]) -> UserFriendlyError:
        """Translate an unknown exception."""
        exception_type = type(exception).__name__

        # Log the full exception for debugging
        logger.error(f"Unknown error during conversion: {exception_type}: {exception}", exc_info=True)

        return UserFriendlyError(
            code="UNKNOWN_ERROR",
            title="Unexpected Error",
            message="An unexpected error occurred during processing.",
            details=f"{exception_type}: {self._sanitize_paths(str(exception))}",
            remediation="Please try again or contact support if the problem persists.",
            help_url=f"{self.HELP_BASE_URL}/troubleshooting",
        )

    def _sanitize_paths(self, text: str) -> str:
        """
        Sanitize file paths in error messages for security and readability.

        Replaces absolute paths with relative paths or generic placeholders
        to avoid exposing sensitive system information.
        """
        if not text:
            return text

        # Replace common system paths with placeholders
        sanitized = text

        # Replace user home directory
        home_path = str(Path.home())
        if home_path in sanitized:
            sanitized = sanitized.replace(home_path, "~")

        # Replace temp directories
        import tempfile

        temp_dir = tempfile.gettempdir()
        if temp_dir in sanitized:
            sanitized = sanitized.replace(temp_dir, "<temp>")

        # Replace very long paths with ellipsis
        # Pattern: /very/long/path/to/file.ext -> .../file.ext
        sanitized = re.sub(r"(/[^/\s]+){4,}/([^/\s]+)$", r".../\2", sanitized)

        return sanitized


# Convenience functions
def translate_error(exception: Exception, context: dict[str, Any] | None = None) -> UserFriendlyError:
    """
    Convenience function to translate an exception.

    Args:
        exception: Exception to translate
        context: Optional context information

    Returns:
        UserFriendlyError with translated message
    """
    translator = ErrorTranslator()
    return translator.translate_exception(exception, context)


def format_error_for_display(error: UserFriendlyError) -> str:
    """
    Format a UserFriendlyError for display in a message box or dialog.

    Args:
        error: UserFriendlyError to format

    Returns:
        Formatted error message string
    """
    parts = [error.message]

    if error.remediation:
        parts.append(f"\nSuggestion: {error.remediation}")

    if error.help_url:
        parts.append(f"\nFor more help, visit: {error.help_url}")

    return "".join(parts)


def log_error_details(error: UserFriendlyError, original_exception: Exception | None = None) -> None:
    """
    Log detailed error information for debugging purposes.

    Args:
        error: UserFriendlyError to log
        original_exception: Original exception (if available)
    """
    logger.error(
        f"Error [{error.code}]: {error.title} - {error.message}",
        extra={
            "error_code": error.code,
            "error_title": error.title,
            "error_field": error.field,
            "error_details": error.details,
        },
        exc_info=original_exception,
    )


# Convenience functions for easy error handling
def to_user_error(err: BaseAppError) -> UserFriendlyError:
    """
    Convert a BaseAppError to a UserFriendlyError.

    Args:
        err: The BaseAppError to convert

    Returns:
        UserFriendlyError suitable for UI display
    """
    translator = ErrorTranslator()
    return translator.from_app_error(err)
