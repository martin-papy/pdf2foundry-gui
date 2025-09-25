"""
Configuration manager for PDF2Foundry GUI.

Provides QSettings-backed configuration management with default fallbacks
and type safety.
"""

import logging
from typing import Any

from PySide6.QtCore import QSettings

from .config import DEFAULT_CONFIG, get_default_output_dir, setup_qsettings

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    QSettings-backed configuration manager with robust defaults.

    Provides type-safe access to configuration values with automatic
    fallback to defaults when keys are missing or have invalid types.
    """

    def __init__(self) -> None:
        """Initialize the ConfigManager with QSettings."""
        # Ensure QSettings is configured with app identifiers
        setup_qsettings()

        # Initialize QSettings with organization and application name
        self._settings = QSettings()

        # Set runtime defaults that depend on system paths
        self._runtime_defaults = DEFAULT_CONFIG.copy()
        if not self._runtime_defaults["output_dir"]:
            self._runtime_defaults["output_dir"] = get_default_output_dir()

    def get(self, key: str, default: Any | None = None) -> Any:
        """
        Get a configuration value with fallback to defaults.

        Args:
            key: Configuration key (can use "/" for nested keys)
            default: Override default value (if None, uses DEFAULT_CONFIG)

        Returns:
            Configuration value with type coercion and default fallback
        """
        # Determine the fallback value
        fallback = default if default is not None else self._runtime_defaults.get(key)

        # Get value from QSettings
        value = self._settings.value(key, fallback)

        # Type coercion and validation
        if fallback is not None:
            try:
                # Coerce to the expected type based on the default
                expected_type = type(fallback)
                if expected_type is bool:
                    # QSettings returns strings for booleans, need special handling
                    value = value.lower() in ("true", "1", "yes", "on") if isinstance(value, str) else bool(value)
                elif expected_type in (int, float, str):
                    value = expected_type(value)
                # For other types (list, dict), trust QSettings or use fallback
                elif not isinstance(value, expected_type):
                    logger.warning(f"Config key '{key}' has unexpected type, using default")
                    value = fallback
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to coerce config key '{key}': {e}, using default")
                value = fallback

        return value

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            key: Configuration key (can use "/" for nested keys)
            value: Value to store (must be JSON-serializable)
        """
        self._settings.setValue(key, value)
        self._settings.sync()  # Ensure immediate persistence

    def load_all(self) -> dict[str, Any]:
        """
        Load all configuration values merged with defaults.

        Returns:
            Dictionary with all configuration keys, using stored values
            where available and defaults for missing keys
        """
        config = self._runtime_defaults.copy()

        # Override with stored values
        for key in config:
            stored_value = self.get(key)
            if stored_value is not None:
                config[key] = stored_value

        return config

    def reset_to_defaults(self) -> None:
        """
        Reset all configuration to default values.

        This clears all stored settings and reverts to defaults.
        """
        # Clear all settings
        self._settings.clear()
        self._settings.sync()

        logger.info("Configuration reset to defaults")

    def export_config(self) -> dict[str, Any]:
        """
        Export current configuration as a dictionary.

        Returns:
            Dictionary containing all current configuration values
        """
        return self.load_all()

    def import_config(self, config: dict[str, Any]) -> None:
        """
        Import configuration from a dictionary with validation.

        Args:
            config: Dictionary containing configuration values
        """
        for key, value in config.items():
            if key in self._runtime_defaults:
                # Validate type against expected default
                expected_type = type(self._runtime_defaults[key])
                try:
                    if expected_type is bool and not isinstance(value, bool):
                        # Handle boolean conversion
                        value = value.lower() in ("true", "1", "yes", "on") if isinstance(value, str) else bool(value)
                    elif expected_type in (int, float, str) and not isinstance(value, expected_type):
                        value = expected_type(value)

                    self.set(key, value)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to import config key '{key}': {e}, skipping")
            else:
                logger.warning(f"Unknown config key '{key}', skipping")

    def get_last_used_preset(self) -> str | None:
        """
        Get the name of the last used preset.

        Returns:
            Preset name or None if no preset was previously selected
        """
        return self.get("last_used_preset") or None

    def set_last_used_preset(self, preset_name: str | None) -> None:
        """
        Set the name of the last used preset.

        Args:
            preset_name: Name of the preset or None to clear
        """
        if preset_name:
            self.set("last_used_preset", preset_name)
        else:
            self._settings.remove("last_used_preset")
            self._settings.sync()

    def has_key(self, key: str) -> bool:
        """
        Check if a configuration key exists in storage.

        Args:
            key: Configuration key to check

        Returns:
            True if the key exists in storage, False otherwise
        """
        return self._settings.contains(key)

    def remove_key(self, key: str) -> None:
        """
        Remove a configuration key from storage.

        Args:
            key: Configuration key to remove
        """
        self._settings.remove(key)
        self._settings.sync()
