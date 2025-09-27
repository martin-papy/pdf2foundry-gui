"""
Backend interface for pdf2foundry core functionality.

This module provides a thread-safe wrapper around the pdf2foundry core conversion
functions, with progress callbacks and cancellation support.
"""

from __future__ import annotations

import contextlib
import dataclasses
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pdf2foundry.cli.conversion import run_conversion_pipeline

from .conversion_config import ConversionConfig
from .errors import BackendError, CancellationError
from .validation import validate_and_normalize

# Type aliases for callbacks
ProgressCallback = Callable[[int, str], None]  # (progress_percent, message)
LogCallback = Callable[[str, str], None]  # (level, message)


@dataclass
class ConversionResult:
    """
    Result of a conversion operation.

    Contains information about the conversion outcome, output paths,
    statistics, and any warnings or errors encountered.
    """

    success: bool
    output_dir: Path
    module_manifest_path: Path | None = None
    pack_path: Path | None = None
    pages_processed: int = 0
    warnings: list[str] = dataclasses.field(default_factory=list)
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Initialize mutable defaults."""
        if self.warnings is None:
            self.warnings = []


class CancellationToken:
    """
    Simple cancellation token for cooperative cancellation.

    This allows long-running operations to be cancelled gracefully
    by checking the token periodically.
    """

    def __init__(self) -> None:
        """Initialize the cancellation token."""
        self._cancelled = threading.Event()

    def cancel(self) -> None:
        """Request cancellation of the operation."""
        self._cancelled.set()

    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested."""
        return self._cancelled.is_set()

    def check_cancelled(self) -> None:
        """
        Check if cancelled and raise an exception if so.

        Raises:
            CancellationError: If cancellation has been requested
        """
        if self.is_cancelled():
            raise CancellationError("Operation was cancelled")


# Legacy aliases for backward compatibility - these are now deprecated
# Use the new error classes from .errors module instead


class BackendInterface:
    """
    Thread-safe interface to pdf2foundry core functionality.

    This class provides a safe wrapper around the core conversion functions,
    with support for progress callbacks, logging, and cancellation.
    """

    def __init__(self) -> None:
        """Initialize the backend interface."""
        self._lock = threading.RLock()
        self._logger = logging.getLogger(__name__)

    def convert(
        self,
        config: ConversionConfig,
        progress_cb: ProgressCallback | None = None,
        log_cb: LogCallback | None = None,
        cancel_token: CancellationToken | None = None,
    ) -> ConversionResult:
        """
        Convert a PDF using the provided configuration.

        Args:
            config: Conversion configuration
            progress_cb: Optional callback for progress updates (percent, message)
            log_cb: Optional callback for log messages (level, message)
            cancel_token: Optional cancellation token

        Returns:
            ConversionResult with outcome and output information

        Raises:
            BackendError: If conversion fails
            CancellationError: If operation is cancelled
        """
        with self._lock:
            try:
                # Validate and normalize the configuration
                validated_config = validate_and_normalize(config)

                # Check for cancellation before starting
                if cancel_token:
                    cancel_token.check_cancelled()

                # Report initial progress
                if progress_cb:
                    progress_cb(0, "Starting conversion...")

                # Convert config to core function kwargs
                kwargs = validated_config.to_core_kwargs()

                # Set up logging capture if log callback is provided
                if log_cb:
                    self._setup_logging_capture(log_cb)

                # Report progress
                if progress_cb:
                    progress_cb(10, "Initializing conversion pipeline...")

                # Check for cancellation
                if cancel_token:
                    cancel_token.check_cancelled()

                # Call the core conversion function
                # Note: The core function doesn't currently support progress callbacks
                # or cancellation, so we can't provide fine-grained progress updates
                self._logger.info(f"Starting conversion of {kwargs['pdf']} to {kwargs['out_dir']}")

                if progress_cb:
                    progress_cb(20, "Running PDF conversion...")

                # This is the actual core call - no subprocess involved
                run_conversion_pipeline(**kwargs)

                # Check for cancellation after completion
                if cancel_token:
                    cancel_token.check_cancelled()

                # Report completion
                if progress_cb:
                    progress_cb(100, "Conversion completed successfully")

                # Build result object
                result = self._build_conversion_result(validated_config)

                self._logger.info(f"Conversion completed successfully: {result.output_dir}")
                return result

            except CancellationError:
                if log_cb:
                    log_cb("INFO", "Conversion was cancelled by user")
                raise

            except Exception as e:
                error_msg = f"Conversion failed: {e!s}"
                # Use thread-safe logging without exc_info to avoid traceback formatting issues
                self._logger.error(error_msg)

                if log_cb:
                    log_cb("ERROR", error_msg)

                # Wrap in BackendError for consistent error handling
                raise BackendError(error_msg, original_error=e) from e

    def _setup_logging_capture(self, log_cb: LogCallback) -> None:
        """
        Set up logging capture to forward log messages to the callback.

        Args:
            log_cb: Callback to receive log messages
        """
        # This is a simplified implementation
        # In a more complete implementation, you might want to:
        # 1. Add a custom logging handler that calls the callback
        # 2. Capture logs from the pdf2foundry modules specifically
        # 3. Filter log levels appropriately

        # For now, we'll just ensure our logger calls the callback
        class CallbackHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                with contextlib.suppress(Exception):
                    # Don't let logging errors break the conversion
                    log_cb(record.levelname, self.format(record))

        handler = CallbackHandler()
        handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))

        # Add handler to pdf2foundry loggers
        pdf2foundry_logger = logging.getLogger("pdf2foundry")
        pdf2foundry_logger.addHandler(handler)
        pdf2foundry_logger.setLevel(logging.INFO)

    def _build_conversion_result(self, config: ConversionConfig) -> ConversionResult:
        """
        Build a ConversionResult from the completed conversion.

        Args:
            config: The validated configuration that was used

        Returns:
            ConversionResult with output information
        """
        output_dir = config.out_dir / config.mod_id

        # Look for expected output files
        manifest_path = output_dir / "module.json"
        pack_path = None

        if config.compile_pack:
            # Look for compiled pack
            pack_name = config.pack_name or f"{config.mod_id}-journals"
            pack_path = output_dir / "packs" / f"{pack_name}.db"

        # Count pages if specified
        pages_processed = len(config.pages) if config.pages else 0

        return ConversionResult(
            success=True,
            output_dir=output_dir,
            module_manifest_path=manifest_path if manifest_path.exists() else None,
            pack_path=pack_path if pack_path and pack_path.exists() else None,
            pages_processed=pages_processed,
            warnings=[],  # Could be populated from conversion logs
        )

    def validate_config(self, config: ConversionConfig) -> tuple[bool, list[str]]:
        """
        Validate a configuration without running the conversion.

        Args:
            config: Configuration to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        try:
            validate_and_normalize(config)
            return True, []
        except Exception as e:
            return False, [str(e)]

    def get_version_info(self) -> dict[str, str]:
        """
        Get version information for the backend.

        Returns:
            Dictionary with version information
        """
        try:
            import pdf2foundry

            return {
                "pdf2foundry": getattr(pdf2foundry, "__version__", "unknown"),
                "backend_interface": "1.0.0",
            }
        except ImportError:
            return {
                "pdf2foundry": "not available",
                "backend_interface": "1.0.0",
            }


# Convenience function for simple conversions
def convert_pdf(
    config: ConversionConfig,
    progress_cb: ProgressCallback | None = None,
    log_cb: LogCallback | None = None,
    cancel_token: CancellationToken | None = None,
) -> ConversionResult:
    """
    Convenience function to convert a PDF with the given configuration.

    Args:
        config: Conversion configuration
        progress_cb: Optional progress callback
        log_cb: Optional log callback
        cancel_token: Optional cancellation token

    Returns:
        ConversionResult with outcome information

    Raises:
        BackendError: If conversion fails
        CancellationError: If operation is cancelled
    """
    interface = BackendInterface()
    return interface.convert(config, progress_cb, log_cb, cancel_token)
