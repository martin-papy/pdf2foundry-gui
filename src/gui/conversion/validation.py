"""
Validation utilities for conversion operations.

This module contains methods for validating conversion prerequisites
such as output directories, disk space, and file permissions.
"""

import logging
import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gui.main_window import MainWindow


class ConversionValidator:
    """Handles validation for conversion operations."""

    def __init__(self, main_window: "MainWindow") -> None:
        """Initialize the validator."""
        self.main_window = main_window
        self._logger = logging.getLogger(__name__)

    def _validate_output_directory(self, output_path: str) -> tuple[bool, str]:
        """
        Validate the output directory for conversion.

        Args:
            output_path: Path to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not output_path or not output_path.strip():
            return False, "Output directory cannot be empty"

        # Normalize the path
        try:
            path_obj = Path(output_path).resolve()
        except (OSError, ValueError) as e:
            return False, f"Invalid path format: {e}"

        # Check for reserved names on Windows
        reserved_names = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        }
        if path_obj.name.upper() in reserved_names:
            return False, f"'{path_obj.name}' is a reserved name and cannot be used"

        # Check path length (Windows has a 260 character limit by default)
        if len(str(path_obj)) > 250:  # Leave some buffer
            return False, "Path is too long (maximum 250 characters)"

        # Check if path exists
        if path_obj.exists():
            # If it exists, it must be a directory
            if not path_obj.is_dir():
                return False, f"Path exists but is not a directory: {path_obj}"

            # Check if we can write to it
            if not os.access(path_obj, os.W_OK):
                return False, f"No write permission for directory: {path_obj}"
        else:
            # If it doesn't exist, check if we can create it
            try:
                # Check parent directory permissions
                parent = path_obj.parent
                if not parent.exists():
                    # Try to create parent directories
                    parent.mkdir(parents=True, exist_ok=True)

                if not os.access(parent, os.W_OK):
                    return False, f"No write permission for parent directory: {parent}"

                # Test directory creation
                path_obj.mkdir(parents=True, exist_ok=True)

                # Test file creation in the directory
                test_file = path_obj / ".write_test"
                try:
                    test_file.write_text("test")
                    test_file.unlink()  # Clean up
                except (OSError, PermissionError) as e:
                    return False, f"Cannot write to directory: {e}"

            except (OSError, PermissionError) as e:
                return False, f"Cannot create directory: {e}"

        return True, ""

    def _check_disk_space(self, output_path: str, estimated_size_mb: int = 100) -> tuple[bool, str]:
        """
        Check if there's sufficient disk space for the conversion.

        Args:
            output_path: Path to check disk space for
            estimated_size_mb: Estimated output size in MB

        Returns:
            Tuple of (has_space, error_message)
        """
        try:
            path_obj = Path(output_path).resolve()

            # Find the existing parent directory to check disk space
            check_path = path_obj
            while not check_path.exists() and check_path.parent != check_path:
                check_path = check_path.parent

            if not check_path.exists():
                return False, "Cannot determine disk space - no accessible parent directory"

            # Get disk usage
            total, used, free = shutil.disk_usage(check_path)

            # Convert to MB
            free_mb = free / (1024 * 1024)

            # Add 50% headroom to the estimated size
            required_mb = estimated_size_mb * 1.5

            if free_mb < required_mb:
                return False, (f"Insufficient disk space. Required: {required_mb:.1f} MB, " f"Available: {free_mb:.1f} MB")

            self._logger.debug(f"Disk space check passed: {free_mb:.1f} MB available, {required_mb:.1f} MB required")
            return True, ""

        except (OSError, ValueError) as e:
            return False, f"Failed to check disk space: {e}"

    def _perform_preflight_checks(self) -> tuple[bool, str]:
        """
        Perform all pre-conversion validation checks.

        Returns:
            Tuple of (all_checks_passed, error_message)
        """
        # Check if conversion is already in progress
        if hasattr(self.main_window, "conversion_handler") and getattr(
            self.main_window.conversion_handler, "_in_progress", False
        ):
            return False, "A conversion is already in progress"

        # Check if cancellation was requested
        if hasattr(self.main_window, "conversion_handler") and getattr(
            self.main_window.conversion_handler, "_cancel_requested", False
        ):
            return False, "Conversion was cancelled"

        # Validate output directory
        if not self.main_window.ui.output_dir_selector:
            return False, "Output directory selector not available"

        output_path = self.main_window.ui.output_dir_selector.path()
        if not output_path:
            return False, "No output directory selected"

        # Validate output directory
        output_valid, output_error = self._validate_output_directory(output_path)
        if not output_valid:
            return False, f"Output directory validation failed: {output_error}"

        # Check disk space
        space_valid, space_error = self._check_disk_space(output_path)
        if not space_valid:
            return False, f"Disk space check failed: {space_error}"

        # Validate PDF file
        pdf_path = self.main_window.file_handler.get_selected_pdf_path()
        if not pdf_path:
            return False, "No PDF file selected"

        if not Path(pdf_path).exists():
            return False, f"Selected PDF file does not exist: {pdf_path}"

        if not os.access(pdf_path, os.R_OK):
            return False, f"Cannot read selected PDF file: {pdf_path}"

        # Validate module inputs
        if not self.main_window.ui.module_id_input or not self.main_window.ui.module_id_input.text().strip():
            return False, "Module ID is required"

        if not self.main_window.ui.module_title_input or not self.main_window.ui.module_title_input.text().strip():
            return False, "Module title is required"

        self._logger.info("All pre-flight checks passed")
        return True, ""
