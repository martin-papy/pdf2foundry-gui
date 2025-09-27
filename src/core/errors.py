"""
Centralized error handling system for PDF2Foundry GUI.

This module provides a comprehensive error taxonomy and custom exception hierarchy
for consistent error handling throughout the application.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Error type categories for consistent error handling."""

    FILE = "file"
    CONVERSION = "conversion"
    SYSTEM = "system"
    VALIDATION = "validation"
    CONFIG = "config"


class ErrorCode(Enum):
    """Specific error codes for common scenarios."""

    # File-related errors
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    FILE_LOCKED = "FILE_LOCKED"
    DISK_FULL = "DISK_FULL"
    PATH_TOO_LONG = "PATH_TOO_LONG"

    # Validation errors
    INVALID_INPUT = "INVALID_INPUT"
    INVALID_FORMAT = "INVALID_FORMAT"
    VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
    REQUIRED_FIELD_MISSING = "REQUIRED_FIELD_MISSING"

    # Configuration errors
    CONFIG_MISSING = "CONFIG_MISSING"
    CONFIG_INVALID = "CONFIG_INVALID"
    CONFIG_PARSE_ERROR = "CONFIG_PARSE_ERROR"

    # Conversion errors
    PDF_CORRUPT = "PDF_CORRUPT"
    PDF_ENCRYPTED = "PDF_ENCRYPTED"
    CONVERSION_FAILED = "CONVERSION_FAILED"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"

    # System errors
    BACKEND_FAILURE = "BACKEND_FAILURE"
    OPERATION_CANCELLED = "OPERATION_CANCELLED"
    TIMEOUT = "TIMEOUT"
    MEMORY_ERROR = "MEMORY_ERROR"
    OS_ERROR = "OS_ERROR"
    DEPENDENCY_MISSING = "DEPENDENCY_MISSING"

    # Generic
    UNKNOWN = "UNKNOWN"


class ErrorSeverity(Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class BaseAppError(Exception):
    """
    Base application error with comprehensive metadata.

    This is the root of all custom application errors, providing
    structured information for consistent error handling and user feedback.
    """

    type: ErrorType
    code: ErrorCode
    user_message: str
    technical_message: str | None = None
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    retriable: bool = False
    context: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        """Return user-friendly error message."""
        return self.user_message

    def __repr__(self) -> str:
        """Return detailed error representation for debugging."""
        return (
            f"{self.__class__.__name__}("
            f"type={self.type.value}, "
            f"code={self.code.value}, "
            f"message='{self.user_message}'"
            f")"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "type": self.type.value,
            "code": self.code.value,
            "user_message": self.user_message,
            "technical_message": self.technical_message,
            "severity": self.severity.value,
            "retriable": self.retriable,
            "context": self.context,
        }


class FileError(BaseAppError):
    """File system related errors."""

    def __init__(
        self,
        code: ErrorCode,
        user_message: str,
        technical_message: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        retriable: bool = False,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(
            type=ErrorType.FILE,
            code=code,
            user_message=user_message,
            technical_message=technical_message,
            severity=severity,
            retriable=retriable,
            context=context or {},
        )


class ConversionError(BaseAppError):
    """PDF conversion related errors."""

    def __init__(
        self,
        code: ErrorCode,
        user_message: str,
        technical_message: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        retriable: bool = True,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(
            type=ErrorType.CONVERSION,
            code=code,
            user_message=user_message,
            technical_message=technical_message,
            severity=severity,
            retriable=retriable,
            context=context or {},
        )


class SystemError(BaseAppError):
    """System and backend related errors."""

    def __init__(
        self,
        code: ErrorCode,
        user_message: str,
        technical_message: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        retriable: bool = False,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(
            type=ErrorType.SYSTEM,
            code=code,
            user_message=user_message,
            technical_message=technical_message,
            severity=severity,
            retriable=retriable,
            context=context or {},
        )


class ValidationError(BaseAppError):
    """Input validation related errors."""

    def __init__(
        self,
        code: ErrorCode,
        user_message: str,
        field: str | None = None,
        technical_message: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        retriable: bool = False,
        context: dict[str, Any] | None = None,
    ):
        context = context or {}
        if field:
            context["field"] = field

        super().__init__(
            type=ErrorType.VALIDATION,
            code=code,
            user_message=user_message,
            technical_message=technical_message,
            severity=severity,
            retriable=retriable,
            context=context,
        )

    @property
    def field(self) -> str | None:
        """Get the field that caused the validation error."""
        return self.context.get("field")


class ConfigError(BaseAppError):
    """Configuration related errors."""

    def __init__(
        self,
        code: ErrorCode,
        user_message: str,
        technical_message: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        retriable: bool = False,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(
            type=ErrorType.CONFIG,
            code=code,
            user_message=user_message,
            technical_message=technical_message,
            severity=severity,
            retriable=retriable,
            context=context or {},
        )


# Exception mapping configuration
_EXCEPTION_MAPPING: dict[type[Exception], tuple[ErrorType, ErrorCode, str]] = {
    FileNotFoundError: (ErrorType.FILE, ErrorCode.FILE_NOT_FOUND, "File not found"),
    PermissionError: (ErrorType.FILE, ErrorCode.PERMISSION_DENIED, "Permission denied"),
    OSError: (ErrorType.SYSTEM, ErrorCode.OS_ERROR, "System error occurred"),
    ValueError: (ErrorType.VALIDATION, ErrorCode.INVALID_INPUT, "Invalid input provided"),
    TimeoutError: (ErrorType.SYSTEM, ErrorCode.TIMEOUT, "Operation timed out"),
    MemoryError: (ErrorType.SYSTEM, ErrorCode.MEMORY_ERROR, "Insufficient memory"),
}


def map_exception(exc: Exception, context: dict[str, Any] | None = None) -> BaseAppError:
    """
    Map a built-in exception to a custom application error.

    Args:
        exc: The exception to map
        context: Optional context information

    Returns:
        BaseAppError instance with appropriate type and metadata
    """
    context = context or {}

    # Handle existing custom errors
    if isinstance(exc, BaseAppError):
        return exc

    # Handle legacy ValidationError from validation.py
    if hasattr(exc, "field") and hasattr(exc, "code") and hasattr(exc, "message"):
        # This is likely the old ValidationError
        return ValidationError(
            code=ErrorCode.INVALID_INPUT,
            user_message=getattr(exc, "message", str(exc)),
            field=getattr(exc, "field", None),
            technical_message=str(exc),
            context=context,
        )

    # Handle legacy BackendError
    if exc.__class__.__name__ == "BackendError":
        original_error = getattr(exc, "original_error", None)
        return SystemError(
            code=ErrorCode.BACKEND_FAILURE,
            user_message=str(exc),
            technical_message=str(original_error) if original_error else None,
            context=context,
        )

    # Handle legacy CancellationError
    if exc.__class__.__name__ == "CancellationError":
        return SystemError(
            code=ErrorCode.OPERATION_CANCELLED,
            user_message="Operation was cancelled",
            technical_message=str(exc),
            retriable=True,
            context=context,
        )

    # Map built-in exceptions
    exc_type = type(exc)
    if exc_type in _EXCEPTION_MAPPING:
        error_type, error_code, default_message = _EXCEPTION_MAPPING[exc_type]

        # Create appropriate error class
        error_class_map = {
            ErrorType.FILE: FileError,
            ErrorType.CONVERSION: ConversionError,
            ErrorType.SYSTEM: SystemError,
            ErrorType.VALIDATION: ValidationError,
            ErrorType.CONFIG: ConfigError,
        }

        error_class = error_class_map[error_type]
        user_message = str(exc) if str(exc) else default_message

        # Special handling for specific error types
        kwargs: dict[str, Any] = {"context": context}
        if error_type == ErrorType.SYSTEM and error_code == ErrorCode.OPERATION_CANCELLED:
            kwargs["retriable"] = True

        result: BaseAppError = error_class(
            code=error_code,
            user_message=user_message,
            technical_message=f"{exc_type.__name__}: {exc}",
            **kwargs,
        )
        return result

    # Fallback for unknown exceptions
    logger.warning(f"Unknown exception type: {exc_type.__name__}: {exc}")
    return SystemError(
        code=ErrorCode.UNKNOWN,
        user_message="An unexpected error occurred",
        technical_message=f"{exc_type.__name__}: {exc}",
        context=context,
    )


def from_exception(exc: Exception, context: dict[str, Any] | None = None) -> BaseAppError:
    """
    Convert any exception to a BaseAppError.

    This is an alias for map_exception for convenience.

    Args:
        exc: The exception to convert
        context: Optional context information

    Returns:
        BaseAppError instance
    """
    return map_exception(exc, context)


# Backward compatibility aliases for legacy code
class LegacyBackendError(SystemError):
    """Legacy BackendError for backward compatibility."""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(
            code=ErrorCode.BACKEND_FAILURE,
            user_message=message,
            technical_message=str(original_error) if original_error else None,
        )
        self.original_error = original_error


class LegacyCancellationError(SystemError):
    """Legacy CancellationError for backward compatibility."""

    def __init__(self, message: str = "Operation was cancelled"):
        super().__init__(
            code=ErrorCode.OPERATION_CANCELLED,
            user_message=message,
            retriable=True,
        )


# Export legacy names for backward compatibility
BackendError = LegacyBackendError
CancellationError = LegacyCancellationError
