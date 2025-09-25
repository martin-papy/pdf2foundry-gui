"""
Configuration management for PDF2Foundry GUI.

This module provides configuration schema, defaults, and management classes
for handling application settings and user presets.
"""

from pathlib import Path
from typing import Any

from PySide6.QtCore import QCoreApplication, QStandardPaths

# Application identifiers for QSettings
APP_ORGANIZATION = "PDF2Foundry"
APP_NAME = "GUI"

# JSON Schema version for preset compatibility
SCHEMA_VERSION = "1.0.0"

# Default configuration with all supported keys and JSON-serializable types
DEFAULT_CONFIG: dict[str, Any] = {
    # General settings
    "author": "",
    "license": "",
    "pack_name": "",
    "output_dir": "",  # Will be set to Documents directory at runtime
    "deterministic_ids": True,
    # Conversion settings
    "toc": True,
    "tables": "auto",  # Options: "auto", "structured", "image-only"
    "ocr": "auto",  # Options: "auto", "on", "off"
    "picture_descriptions": False,
    "vlm_repo": "",
    "pages": "",
    # Debug settings
    "verbose": False,
    "log_level": "INFO",  # Options: "DEBUG", "INFO", "WARNING", "ERROR"
    "dry_run": False,
    "keep_temp": False,
    "log_file": "",
    "export_debug_path": "",
    # UI state (not part of presets)
    "last_open_dir": "",
    "last_used_preset": "",
}

# JSON Schema for preset validation (draft-07)
PRESET_JSON_SCHEMA: dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "https://pdf2foundry.com/schemas/preset-v1.json",
    "title": "PDF2Foundry GUI Preset",
    "description": "Configuration preset for PDF2Foundry GUI application",
    "type": "object",
    "required": ["schema_version", "name", "config"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {
            "type": "string",
            "const": SCHEMA_VERSION,
            "description": "Schema version for compatibility checking",
        },
        "name": {"type": "string", "minLength": 1, "maxLength": 100, "description": "Human-readable preset name"},
        "description": {"type": "string", "maxLength": 500, "description": "Optional preset description"},
        "created_at": {"type": "string", "format": "date-time", "description": "ISO 8601 timestamp when preset was created"},
        "config": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                # General settings
                "author": {"type": "string"},
                "license": {"type": "string"},
                "pack_name": {"type": "string"},
                "output_dir": {"type": "string"},
                "deterministic_ids": {"type": "boolean"},
                # Conversion settings
                "toc": {"type": "boolean"},
                "tables": {"type": "string", "enum": ["auto", "structured", "image-only"]},
                "ocr": {"type": "string", "enum": ["auto", "on", "off"]},
                "picture_descriptions": {"type": "boolean"},
                "vlm_repo": {"type": "string"},
                "pages": {"type": "string"},
                # Debug settings
                "verbose": {"type": "boolean"},
                "log_level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR"]},
                "dry_run": {"type": "boolean"},
                "keep_temp": {"type": "boolean"},
                "log_file": {"type": "string"},
                "export_debug_path": {"type": "string"},
            },
        },
    },
}


def get_app_config_dir() -> Path:
    """
    Get the application configuration directory using QStandardPaths.

    Returns:
        Path to the writable configuration directory for this application
    """
    config_location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.ConfigLocation)
    return Path(config_location) / APP_ORGANIZATION / APP_NAME


def get_presets_dir() -> Path:
    """
    Get the directory where presets are stored.

    Returns:
        Path to the presets directory
    """
    return get_app_config_dir() / "presets"


def sanitize_preset_name(name: str) -> str:
    """
    Sanitize a preset name to create a safe filename.

    Converts to lowercase, replaces spaces and special characters with hyphens,
    and removes any characters that aren't alphanumeric, hyphens, or underscores.

    Args:
        name: The human-readable preset name

    Returns:
        A sanitized filename-safe string
    """
    # Convert to lowercase and replace spaces with hyphens
    sanitized = name.lower().replace(" ", "-")

    # Keep only alphanumeric, hyphens, and underscores
    sanitized = "".join(c for c in sanitized if c.isalnum() or c in "-_")

    # Remove multiple consecutive hyphens
    while "--" in sanitized:
        sanitized = sanitized.replace("--", "-")

    # Remove leading/trailing hyphens
    sanitized = sanitized.strip("-")

    # Ensure we have something left
    if not sanitized:
        sanitized = "preset"

    return sanitized


def get_default_output_dir() -> str:
    """
    Get the default output directory for the application.

    Returns:
        Path to the user's Documents directory, or current working directory as fallback
    """
    docs_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
    if docs_dir and Path(docs_dir).exists():
        return docs_dir
    return str(Path.cwd())


def ensure_app_directories() -> None:
    """
    Ensure that application directories exist.

    Creates the configuration and presets directories if they don't exist.
    """
    config_dir = get_app_config_dir()
    presets_dir = get_presets_dir()

    config_dir.mkdir(parents=True, exist_ok=True)
    presets_dir.mkdir(parents=True, exist_ok=True)


def setup_qsettings() -> None:
    """
    Configure QSettings with application identifiers.

    This should be called early in application startup to ensure
    QSettings uses the correct organization and application names.
    """
    QCoreApplication.setOrganizationName(APP_ORGANIZATION)
    QCoreApplication.setApplicationName(APP_NAME)
