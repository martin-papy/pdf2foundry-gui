"""
Directory validation utilities for the output directory selector widget.
"""

import os
from pathlib import Path

from PySide6.QtCore import QStandardPaths


class DirectoryValidator:
    """Handles validation logic for directory paths."""

    @staticmethod
    def get_default_output_dir() -> Path | None:
        """
        Get the default output directory.

        Returns:
            The default output directory, or None if none available
        """
        # Try Documents folder first
        documents_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)

        if documents_path:
            documents_dir = Path(documents_path)
            if documents_dir.exists() and DirectoryValidator.is_directory_writable(documents_dir):
                return documents_dir

        # Fall back to current working directory
        cwd = Path.cwd()
        if DirectoryValidator.is_directory_writable(cwd):
            return cwd

        return None

    @staticmethod
    def is_directory_writable(path: Path) -> bool:
        """
        Check if a directory is writable.

        Args:
            path: Path to check

        Returns:
            True if the directory is writable, False otherwise
        """
        if not path.exists() or not path.is_dir():
            return False

        return os.access(path, os.W_OK)

    @staticmethod
    def validate_path(path: Path | str) -> tuple[bool, str]:
        """
        Validate a directory path for use as output directory.

        Args:
            path: Path to validate (string or Path object)

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not path:
            return False, "Please select an output directory"

        try:
            path_obj = Path(path).expanduser().resolve()
        except (OSError, ValueError) as e:
            return False, f"Invalid path: {e}"

        # Check if path exists
        if not path_obj.exists():
            # Check if parent directory exists and is writable
            parent = path_obj.parent
            if not parent.exists():
                return False, f"Parent directory does not exist: {parent}"
            if not DirectoryValidator.is_directory_writable(parent):
                return False, f"Cannot create directory: no write permission to {parent}"
            return True, f"Directory will be created: {path_obj}"

        # Path exists - check if it's a directory
        if not path_obj.is_dir():
            return False, f"Path is not a directory: {path_obj}"

        # Check if directory is writable
        if not DirectoryValidator.is_directory_writable(path_obj):
            return False, f"Directory is not writable: {path_obj}"

        return True, f"Valid output directory: {path_obj}"
