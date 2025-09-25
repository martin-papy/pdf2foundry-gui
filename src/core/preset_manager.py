"""
Preset manager for PDF2Foundry GUI.

Provides CRUD operations for configuration presets with JSON serialization,
schema validation, and atomic file operations.
"""

import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import jsonschema

from .config import (
    PRESET_JSON_SCHEMA,
    SCHEMA_VERSION,
    ensure_app_directories,
    get_presets_dir,
    sanitize_preset_name,
)

logger = logging.getLogger(__name__)


class PresetError(Exception):
    """Base exception for preset operations."""

    pass


class PresetValidationError(PresetError):
    """Exception raised when preset validation fails."""

    pass


class PresetIOError(PresetError):
    """Exception raised when preset I/O operations fail."""

    pass


class PresetManager:
    """
    Manager for configuration presets with JSON storage and validation.

    Provides safe CRUD operations for presets with atomic file writes,
    schema validation, and corruption handling.
    """

    def __init__(self) -> None:
        """Initialize the PresetManager."""
        # Ensure directories exist
        ensure_app_directories()

        self._presets_dir = get_presets_dir()
        self._preset_cache: list[str] | None = None

        logger.debug(f"PresetManager initialized with directory: {self._presets_dir}")

    def save_preset(self, name: str, config: dict[str, Any], overwrite: bool = False) -> None:
        """
        Save a configuration preset with validation.

        Args:
            name: Human-readable preset name
            config: Configuration dictionary to save
            overwrite: Whether to overwrite existing preset

        Raises:
            PresetValidationError: If the preset data is invalid
            PresetIOError: If file operations fail
            PresetError: If preset exists and overwrite is False
        """
        if not name or not name.strip():
            raise PresetValidationError("Preset name cannot be empty")

        name = name.strip()
        filename = sanitize_preset_name(name)

        if not filename:
            raise PresetValidationError(f"Invalid preset name: '{name}'")

        preset_path = self._presets_dir / f"{filename}.json"

        # Check for existing preset
        if preset_path.exists() and not overwrite:
            raise PresetError(f"Preset '{name}' already exists")

        # Create preset data structure
        preset_data = {
            "schema_version": SCHEMA_VERSION,
            "name": name,
            "created_at": datetime.now().isoformat(),
            "config": config,
        }

        # Validate against schema
        try:
            jsonschema.validate(preset_data, PRESET_JSON_SCHEMA)
        except jsonschema.ValidationError as e:
            raise PresetValidationError(f"Preset validation failed: {e.message}") from e

        # Write atomically using temporary file
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", dir=self._presets_dir, delete=False, encoding="utf-8"
            ) as temp_file:
                json.dump(preset_data, temp_file, ensure_ascii=False, indent=2, sort_keys=True)
                temp_path = temp_file.name

            # Atomic move to final location
            os.replace(temp_path, preset_path)

            logger.info(f"Saved preset '{name}' to {preset_path}")

            # Invalidate cache
            self._preset_cache = None

        except (OSError, json.JSONDecodeError) as e:
            # Clean up temp file if it exists
            try:
                if "temp_path" in locals():
                    os.unlink(temp_path)
            except OSError:
                pass
            raise PresetIOError(f"Failed to save preset '{name}': {e}") from e

    def load_preset(self, name: str) -> dict[str, Any]:
        """
        Load a configuration preset by name.

        Args:
            name: Preset name to load

        Returns:
            Configuration dictionary from the preset

        Raises:
            PresetError: If preset doesn't exist
            PresetValidationError: If preset is corrupted or invalid
            PresetIOError: If file operations fail
        """
        filename = sanitize_preset_name(name)
        preset_path = self._presets_dir / f"{filename}.json"

        if not preset_path.exists():
            raise PresetError(f"Preset '{name}' not found")

        try:
            with open(preset_path, encoding="utf-8") as f:
                preset_data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            raise PresetIOError(f"Failed to load preset '{name}': {e}") from e

        # Validate schema version compatibility
        schema_version = preset_data.get("schema_version")
        if schema_version != SCHEMA_VERSION:
            logger.warning(f"Preset '{name}' has schema version {schema_version}, expected {SCHEMA_VERSION}")
            # For now, we'll try to load it anyway, but in the future we might need migration

        # Validate against schema
        try:
            jsonschema.validate(preset_data, PRESET_JSON_SCHEMA)
        except jsonschema.ValidationError as e:
            raise PresetValidationError(f"Preset '{name}' is corrupted: {e.message}") from e

        logger.debug(f"Loaded preset '{name}' from {preset_path}")
        return preset_data["config"]  # type: ignore[no-any-return]

    def delete_preset(self, name: str) -> None:
        """
        Delete a preset by name.

        Args:
            name: Preset name to delete

        Raises:
            PresetError: If preset doesn't exist
            PresetIOError: If file operations fail
        """
        filename = sanitize_preset_name(name)
        preset_path = self._presets_dir / f"{filename}.json"

        if not preset_path.exists():
            raise PresetError(f"Preset '{name}' not found")

        try:
            preset_path.unlink()
            logger.info(f"Deleted preset '{name}' from {preset_path}")

            # Invalidate cache
            self._preset_cache = None

        except OSError as e:
            raise PresetIOError(f"Failed to delete preset '{name}': {e}") from e

    def list_presets(self) -> list[str]:
        """
        List all available presets.

        Returns:
            List of preset names (human-readable names from JSON, not filenames)
        """
        if self._preset_cache is not None:
            return self._preset_cache.copy()

        presets = []

        try:
            for preset_file in self._presets_dir.glob("*.json"):
                try:
                    with open(preset_file, encoding="utf-8") as f:
                        preset_data = json.load(f)

                    # Extract human-readable name
                    preset_name = preset_data.get("name")
                    if preset_name:
                        presets.append(preset_name)
                    else:
                        logger.warning(f"Preset file {preset_file} missing name field")

                except (json.JSONDecodeError, OSError, KeyError) as e:
                    logger.warning(f"Failed to read preset file {preset_file}: {e}")
                    continue

        except OSError as e:
            logger.error(f"Failed to list presets directory: {e}")
            return []

        # Sort alphabetically and cache
        presets.sort()
        self._preset_cache = presets

        return presets.copy()

    def preset_exists(self, name: str) -> bool:
        """
        Check if a preset exists.

        Args:
            name: Preset name to check

        Returns:
            True if preset exists, False otherwise
        """
        filename = sanitize_preset_name(name)
        preset_path = self._presets_dir / f"{filename}.json"
        return preset_path.exists()

    def get_preset_info(self, name: str) -> dict[str, Any]:
        """
        Get metadata about a preset without loading its configuration.

        Args:
            name: Preset name

        Returns:
            Dictionary with preset metadata (name, created_at, etc.)

        Raises:
            PresetError: If preset doesn't exist
            PresetIOError: If file operations fail
        """
        filename = sanitize_preset_name(name)
        preset_path = self._presets_dir / f"{filename}.json"

        if not preset_path.exists():
            raise PresetError(f"Preset '{name}' not found")

        try:
            with open(preset_path, encoding="utf-8") as f:
                preset_data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            raise PresetIOError(f"Failed to read preset '{name}': {e}") from e

        # Return metadata without config
        metadata = preset_data.copy()
        metadata.pop("config", None)
        return metadata  # type: ignore[no-any-return]

    def get_preset_path(self, name: str) -> Path:
        """
        Get the file path for a preset.

        Args:
            name: Preset name

        Returns:
            Path object for the preset file
        """
        filename = sanitize_preset_name(name)
        return self._presets_dir / f"{filename}.json"

    def clear_cache(self) -> None:
        """Clear the preset list cache."""
        self._preset_cache = None

    def validate_preset_file(self, preset_path: Path) -> bool:
        """
        Validate a preset file against the schema.

        Args:
            preset_path: Path to the preset file

        Returns:
            True if valid, False otherwise
        """
        try:
            with open(preset_path, encoding="utf-8") as f:
                preset_data = json.load(f)

            jsonschema.validate(preset_data, PRESET_JSON_SCHEMA)
            return True

        except (OSError, json.JSONDecodeError, jsonschema.ValidationError):
            return False
