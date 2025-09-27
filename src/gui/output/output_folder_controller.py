"""Output folder controller for managing output directory paths and validation.

This module provides the OutputFolderController class which serves as the single
source of truth for output directory management, including validation,
normalization, and persistence.
"""

import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from PySide6.QtCore import QStandardPaths

from core.config_manager import ConfigManager
from gui.utils.fs import open_in_file_manager

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of output path validation.

    Attributes:
        valid: Whether the path is valid and ready for use.
        normalized_path: The normalized absolute path.
        message: Human-readable status or error message.
        level: Severity level of the message.
        can_create: Whether the path can be created if it doesn't exist.
        writable: Whether the path is writable (only valid if exists).
    """

    valid: bool
    normalized_path: Path
    message: str
    level: Literal["info", "warning", "error"]
    can_create: bool = False
    writable: bool = False


class OutputFolderController:
    """Controller for managing output folder paths with validation and persistence.

    This class serves as the single source of truth for output directory management,
    providing validation, normalization, and integration with the ConfigManager
    for persistence.
    """

    def __init__(self, config_manager: ConfigManager | None = None) -> None:
        """Initialize the OutputFolderController.

        Args:
            config_manager: Optional ConfigManager instance. If None, creates a new one.
        """
        self._config = config_manager or ConfigManager()
        self._current_path: Path | None = None
        self._default_path: Path | None = None

        # Load the current path from configuration
        self._load_current_path()

    def _load_current_path(self) -> None:
        """Load the current output path from configuration."""
        stored_path = self._config.get("paths/output_dir")
        if stored_path:
            try:
                self._current_path = Path(stored_path).expanduser().resolve(strict=False)
            except (OSError, ValueError) as e:
                logger.warning(f"Failed to load stored output path '{stored_path}': {e}")
                self._current_path = None

        # If no valid stored path, use default
        if not self._current_path:
            self._current_path = self.default_path()

    def current_path(self) -> Path:
        """Get the current output path.

        Returns:
            The current output directory path.
        """
        if not self._current_path:
            self._current_path = self.default_path()
        return self._current_path

    def set_path(self, path: Path, source: Literal["user", "settings", "reset"]) -> ValidationResult:
        """Set the current output path with validation.

        Args:
            path: The new output directory path.
            source: Source of the path change for logging.

        Returns:
            ValidationResult with the outcome of the operation.
        """
        # Normalize the path
        try:
            normalized = path.expanduser().resolve(strict=False)
        except (OSError, ValueError) as e:
            return ValidationResult(valid=False, normalized_path=path, message=f"Invalid path: {e}", level="error")

        # Validate the path
        result = self._validate_path(normalized)

        # If valid or can be created, update the current path and persist
        if result.valid or result.can_create:
            self._current_path = normalized
            self._config.set("paths/output_dir", str(normalized))
            logger.info(f"Output path set to {normalized} (source: {source})")

        return result

    def default_path(self) -> Path:
        """Get the default output path.

        Returns:
            The default output directory path.
        """
        if not self._default_path:
            # Check if we have a stored default
            stored_default = self._config.get("paths/default_output_dir")
            if stored_default:
                try:
                    self._default_path = Path(stored_default).expanduser().resolve(strict=False)
                except (OSError, ValueError):
                    stored_default = None

            # If no stored default or it's invalid, compute a new one
            if not stored_default:
                docs_location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
                if docs_location:
                    self._default_path = Path(docs_location) / "pdf2foundry"
                else:
                    # Fallback to current working directory
                    self._default_path = Path.cwd() / "pdf2foundry"

                # Store the computed default
                self._config.set("paths/default_output_dir", str(self._default_path))

        assert self._default_path is not None  # Help MyPy understand this is not None
        return self._default_path

    def reset_to_default(self) -> ValidationResult:
        """Reset the output path to the default.

        Returns:
            ValidationResult with the outcome of the operation.
        """
        default = self.default_path()
        return self.set_path(default, "reset")

    def ensure_exists(self, path: Path, create_if_missing: bool = True) -> bool:
        """Ensure that a directory exists, optionally creating it.

        Args:
            path: The directory path to check/create.
            create_if_missing: Whether to create the directory if it doesn't exist.

        Returns:
            True if the directory exists (or was created), False otherwise.
        """
        if path.exists():
            return path.is_dir()

        if not create_if_missing:
            return False

        try:
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created output directory: {path}")
            return True
        except (OSError, PermissionError) as e:
            logger.error(f"Failed to create directory {path}: {e}")
            return False

    def is_writable(self, path: Path) -> bool:
        """Check if a directory is writable.

        Args:
            path: The directory path to check.

        Returns:
            True if the directory is writable, False otherwise.
        """
        if not path.exists() or not path.is_dir():
            return False

        # Try to create a temporary file in the directory
        try:
            with tempfile.NamedTemporaryFile(dir=path, delete=True):
                pass
            return True
        except (OSError, PermissionError):
            # Fallback to os.access check
            try:
                return os.access(path, os.W_OK)
            except OSError:
                return False

    def open_in_file_manager(self, path: Path) -> bool:
        """Open a directory in the system file manager.

        Args:
            path: The directory path to open.

        Returns:
            True if successful, False otherwise.
        """
        return open_in_file_manager(path)

    def last_export_path(self) -> Path | None:
        """Get the last export path.

        Returns:
            The last export directory path, or None if not set.
        """
        stored_path = self._config.get("paths/last_export_dir")
        if stored_path:
            try:
                return Path(stored_path).expanduser().resolve(strict=False)
            except (OSError, ValueError) as e:
                logger.warning(f"Failed to load last export path '{stored_path}': {e}")
        return None

    def set_last_export_path(self, path: Path) -> None:
        """Set the last export path.

        Args:
            path: The directory path where the last export occurred.
        """
        try:
            normalized = path.expanduser().resolve(strict=False)
            self._config.set("paths/last_export_dir", str(normalized))
            logger.debug(f"Last export path set to: {normalized}")
        except (OSError, ValueError) as e:
            logger.warning(f"Failed to set last export path '{path}': {e}")

    def _validate_path(self, path: Path) -> ValidationResult:
        """Validate an output directory path.

        Args:
            path: The normalized path to validate.

        Returns:
            ValidationResult with validation details.
        """
        # Check if path exists
        if not path.exists():
            # Check if parent exists and is writable
            parent = path.parent
            if parent.exists() and parent.is_dir():
                if self.is_writable(parent):
                    return ValidationResult(
                        valid=False,
                        normalized_path=path,
                        message="Folder will be created when needed",
                        level="info",
                        can_create=True,
                        writable=False,
                    )
                else:
                    return ValidationResult(
                        valid=False,
                        normalized_path=path,
                        message="Cannot create folder: parent directory is not writable",
                        level="error",
                        can_create=False,
                        writable=False,
                    )
            else:
                return ValidationResult(
                    valid=False,
                    normalized_path=path,
                    message="Path is invalid or parent directory does not exist",
                    level="error",
                    can_create=False,
                    writable=False,
                )

        # Path exists - check if it's a directory
        if not path.is_dir():
            return ValidationResult(
                valid=False,
                normalized_path=path,
                message="Path exists but is not a directory",
                level="error",
                can_create=False,
                writable=False,
            )

        # Check if directory is writable
        writable = self.is_writable(path)
        if not writable:
            return ValidationResult(
                valid=False,
                normalized_path=path,
                message="Directory is not writable",
                level="error",
                can_create=False,
                writable=False,
            )

        # All checks passed
        return ValidationResult(
            valid=True,
            normalized_path=path,
            message="Directory is ready for use",
            level="info",
            can_create=True,
            writable=True,
        )
