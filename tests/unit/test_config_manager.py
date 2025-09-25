"""
Tests for the ConfigManager class.
"""

import tempfile
from unittest.mock import Mock, patch

from core.config_manager import ConfigManager


class TestConfigManager:
    """Test cases for ConfigManager."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        # Use a temporary directory for test settings
        self.temp_dir = tempfile.mkdtemp()

        # Mock QSettings to use temporary location
        self.settings_patcher = patch("core.config_manager.QSettings")
        self.mock_qsettings_class = self.settings_patcher.start()
        self.mock_qsettings = Mock()
        self.mock_qsettings_class.return_value = self.mock_qsettings

        # Mock setup_qsettings
        self.setup_patcher = patch("core.config_manager.setup_qsettings")
        self.mock_setup = self.setup_patcher.start()

        # Mock get_default_output_dir
        self.output_dir_patcher = patch("core.config_manager.get_default_output_dir")
        self.mock_output_dir = self.output_dir_patcher.start()
        self.mock_output_dir.return_value = "/tmp/test_output"

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        self.settings_patcher.stop()
        self.setup_patcher.stop()
        self.output_dir_patcher.stop()

    def test_init(self) -> None:
        """Test ConfigManager initialization."""
        config_manager = ConfigManager()

        # Verify setup_qsettings was called
        self.mock_setup.assert_called_once()

        # Verify QSettings was initialized correctly
        self.mock_qsettings_class.assert_called_once()

        # Verify runtime defaults include output directory
        assert config_manager._runtime_defaults["output_dir"] == "/tmp/test_output"

    def test_get_with_default(self) -> None:
        """Test getting a value with default fallback."""
        config_manager = ConfigManager()

        # Mock QSettings.value to return the default (QSettings behavior)
        self.mock_qsettings.value.return_value = ""

        # Test getting a key that doesn't exist
        result = config_manager.get("author")
        assert result == ""  # Default from DEFAULT_CONFIG

        # Verify QSettings.value was called correctly
        self.mock_qsettings.value.assert_called_with("author", "")

    def test_get_with_stored_value(self) -> None:
        """Test getting a stored value."""
        config_manager = ConfigManager()

        # Mock QSettings.value to return a stored value
        self.mock_qsettings.value.return_value = "Test Author"

        result = config_manager.get("author")
        assert result == "Test Author"

    def test_get_boolean_coercion(self) -> None:
        """Test boolean type coercion from QSettings."""
        config_manager = ConfigManager()

        # Test string "true" -> True
        self.mock_qsettings.value.return_value = "true"
        result = config_manager.get("deterministic_ids")
        assert result is True

        # Test string "false" -> False
        self.mock_qsettings.value.return_value = "false"
        result = config_manager.get("deterministic_ids")
        assert result is False

        # Test integer 1 -> True
        self.mock_qsettings.value.return_value = 1
        result = config_manager.get("deterministic_ids")
        assert result is True

    def test_set(self) -> None:
        """Test setting a value."""
        config_manager = ConfigManager()

        config_manager.set("author", "Test Author")

        # Verify QSettings.setValue and sync were called
        self.mock_qsettings.setValue.assert_called_with("author", "Test Author")
        self.mock_qsettings.sync.assert_called_once()

    def test_load_all(self) -> None:
        """Test loading all configuration values."""
        config_manager = ConfigManager()

        # Mock some stored values
        def mock_value(key: str, default: any) -> any:
            stored_values = {"author": "Test Author", "license": "MIT", "deterministic_ids": "true"}
            return stored_values.get(key, default)

        self.mock_qsettings.value.side_effect = mock_value

        result = config_manager.load_all()

        # Verify stored values override defaults
        assert result["author"] == "Test Author"
        assert result["license"] == "MIT"
        assert result["deterministic_ids"] is True  # Should be coerced to boolean

        # Verify defaults are preserved for unset keys
        assert result["pack_name"] == ""  # Default value
        assert result["toc"] is True  # Default value

    def test_reset_to_defaults(self) -> None:
        """Test resetting configuration to defaults."""
        config_manager = ConfigManager()

        config_manager.reset_to_defaults()

        # Verify QSettings.clear and sync were called
        self.mock_qsettings.clear.assert_called_once()
        self.mock_qsettings.sync.assert_called_once()

    def test_export_config(self) -> None:
        """Test exporting configuration."""
        config_manager = ConfigManager()

        # Mock load_all to return test data
        with patch.object(config_manager, "load_all") as mock_load_all:
            test_config = {"author": "Test", "license": "MIT"}
            mock_load_all.return_value = test_config

            result = config_manager.export_config()
            assert result == test_config

    def test_import_config(self) -> None:
        """Test importing configuration."""
        config_manager = ConfigManager()

        test_config = {
            "author": "Test Author",
            "license": "MIT",
            "deterministic_ids": True,
            "unknown_key": "should be ignored",
        }

        config_manager.import_config(test_config)

        # Verify known keys were set
        expected_calls = [("author", "Test Author"), ("license", "MIT"), ("deterministic_ids", True)]

        for key, value in expected_calls:
            self.mock_qsettings.setValue.assert_any_call(key, value)

        # Verify unknown key was not set (check that it's not in the call args)
        call_args_list = self.mock_qsettings.setValue.call_args_list
        unknown_key_calls = [call for call in call_args_list if call[0][0] == "unknown_key"]
        assert len(unknown_key_calls) == 0

    def test_last_used_preset(self) -> None:
        """Test last used preset management."""
        config_manager = ConfigManager()

        # Test getting when not set
        self.mock_qsettings.value.return_value = ""
        result = config_manager.get_last_used_preset()
        assert result is None

        # Test setting
        config_manager.set_last_used_preset("My Preset")
        self.mock_qsettings.setValue.assert_called_with("last_used_preset", "My Preset")

        # Test clearing
        config_manager.set_last_used_preset(None)
        self.mock_qsettings.remove.assert_called_with("last_used_preset")

    def test_has_key(self) -> None:
        """Test checking if a key exists."""
        config_manager = ConfigManager()

        self.mock_qsettings.contains.return_value = True
        result = config_manager.has_key("author")
        assert result is True

        self.mock_qsettings.contains.assert_called_with("author")

    def test_remove_key(self) -> None:
        """Test removing a key."""
        config_manager = ConfigManager()

        config_manager.remove_key("author")

        self.mock_qsettings.remove.assert_called_with("author")
        self.mock_qsettings.sync.assert_called_once()

    def test_type_coercion_error_handling(self) -> None:
        """Test handling of type coercion errors."""
        config_manager = ConfigManager()

        # Mock QSettings to return invalid type for boolean
        self.mock_qsettings.value.return_value = object()  # Invalid type

        # Should fall back to default
        result = config_manager.get("deterministic_ids")
        assert result is True  # Default value
