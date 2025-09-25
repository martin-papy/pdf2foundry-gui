"""
Tests for the PresetManager class.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from core.preset_manager import PresetError, PresetIOError, PresetManager, PresetValidationError


class TestPresetManager:
    """Test cases for PresetManager."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        # Create temporary directory for presets
        self.temp_dir = tempfile.mkdtemp()
        self.presets_dir = Path(self.temp_dir) / "presets"
        self.presets_dir.mkdir(parents=True, exist_ok=True)

        # Mock the preset directory functions
        self.ensure_dirs_patcher = patch("core.preset_manager.ensure_app_directories")
        self.mock_ensure_dirs = self.ensure_dirs_patcher.start()

        self.get_presets_dir_patcher = patch("core.preset_manager.get_presets_dir")
        self.mock_get_presets_dir = self.get_presets_dir_patcher.start()
        self.mock_get_presets_dir.return_value = self.presets_dir

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        self.ensure_dirs_patcher.stop()
        self.get_presets_dir_patcher.stop()

        # Clean up temporary files
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init(self) -> None:
        """Test PresetManager initialization."""
        preset_manager = PresetManager()

        # Verify directories were ensured
        self.mock_ensure_dirs.assert_called_once()

        # Verify presets directory was set
        assert preset_manager._presets_dir == self.presets_dir

    def test_save_preset_new(self) -> None:
        """Test saving a new preset."""
        preset_manager = PresetManager()

        config = {"author": "Test Author", "license": "MIT", "deterministic_ids": True}

        preset_manager.save_preset("Test Preset", config)

        # Verify file was created
        preset_file = self.presets_dir / "test-preset.json"
        assert preset_file.exists()

        # Verify file contents
        with open(preset_file, encoding="utf-8") as f:
            data = json.load(f)

        assert data["name"] == "Test Preset"
        assert data["schema_version"] == "1.0.0"
        assert data["config"] == config
        assert "created_at" in data

    def test_save_preset_overwrite_denied(self) -> None:
        """Test saving preset when overwrite is denied."""
        preset_manager = PresetManager()

        # Create existing preset
        config = {"author": "Original"}
        preset_manager.save_preset("Test Preset", config)

        # Try to save again without overwrite
        with pytest.raises(PresetError, match="already exists"):
            preset_manager.save_preset("Test Preset", {"author": "New"}, overwrite=False)

    def test_save_preset_overwrite_allowed(self) -> None:
        """Test saving preset with overwrite allowed."""
        preset_manager = PresetManager()

        # Create existing preset
        config1 = {"author": "Original"}
        preset_manager.save_preset("Test Preset", config1)

        # Overwrite with new config
        config2 = {"author": "Updated"}
        preset_manager.save_preset("Test Preset", config2, overwrite=True)

        # Verify updated content
        loaded_config = preset_manager.load_preset("Test Preset")
        assert loaded_config["author"] == "Updated"

    def test_save_preset_invalid_name(self) -> None:
        """Test saving preset with invalid name."""
        preset_manager = PresetManager()

        with pytest.raises(PresetValidationError, match="cannot be empty"):
            preset_manager.save_preset("", {"author": "Test"})

        with pytest.raises(PresetValidationError, match="cannot be empty"):
            preset_manager.save_preset("   ", {"author": "Test"})

    def test_load_preset_success(self) -> None:
        """Test loading an existing preset."""
        preset_manager = PresetManager()

        # Save a preset first
        config = {"author": "Test Author", "license": "MIT", "deterministic_ids": True}
        preset_manager.save_preset("Test Preset", config)

        # Load it back
        loaded_config = preset_manager.load_preset("Test Preset")
        assert loaded_config == config

    def test_load_preset_not_found(self) -> None:
        """Test loading a non-existent preset."""
        preset_manager = PresetManager()

        with pytest.raises(PresetError, match="not found"):
            preset_manager.load_preset("Non-existent Preset")

    def test_load_preset_corrupted(self) -> None:
        """Test loading a corrupted preset file."""
        preset_manager = PresetManager()

        # Create corrupted file
        preset_file = self.presets_dir / "corrupted.json"
        with open(preset_file, "w", encoding="utf-8") as f:
            f.write("invalid json {")

        with pytest.raises(PresetIOError, match="Failed to load"):
            preset_manager.load_preset("corrupted")

    def test_delete_preset_success(self) -> None:
        """Test deleting an existing preset."""
        preset_manager = PresetManager()

        # Save a preset first
        config = {"author": "Test"}
        preset_manager.save_preset("Test Preset", config)

        # Verify it exists
        assert preset_manager.preset_exists("Test Preset")

        # Delete it
        preset_manager.delete_preset("Test Preset")

        # Verify it's gone
        assert not preset_manager.preset_exists("Test Preset")

    def test_delete_preset_not_found(self) -> None:
        """Test deleting a non-existent preset."""
        preset_manager = PresetManager()

        with pytest.raises(PresetError, match="not found"):
            preset_manager.delete_preset("Non-existent Preset")

    def test_list_presets(self) -> None:
        """Test listing available presets."""
        preset_manager = PresetManager()

        # Initially empty
        presets = preset_manager.list_presets()
        assert presets == []

        # Add some presets
        preset_manager.save_preset("Preset A", {"author": "A"})
        preset_manager.save_preset("Preset B", {"author": "B"})
        preset_manager.save_preset("Preset C", {"author": "C"})

        # List should be sorted
        presets = preset_manager.list_presets()
        assert presets == ["Preset A", "Preset B", "Preset C"]

    def test_list_presets_with_corrupted_file(self) -> None:
        """Test listing presets with a corrupted file present."""
        preset_manager = PresetManager()

        # Add valid preset
        preset_manager.save_preset("Valid Preset", {"author": "Test"})

        # Add corrupted file
        corrupted_file = self.presets_dir / "corrupted.json"
        with open(corrupted_file, "w", encoding="utf-8") as f:
            f.write("invalid json")

        # Should return only valid presets
        presets = preset_manager.list_presets()
        assert presets == ["Valid Preset"]

    def test_preset_exists(self) -> None:
        """Test checking if preset exists."""
        preset_manager = PresetManager()

        # Initially doesn't exist
        assert not preset_manager.preset_exists("Test Preset")

        # Create preset
        preset_manager.save_preset("Test Preset", {"author": "Test"})

        # Now it exists
        assert preset_manager.preset_exists("Test Preset")

    def test_get_preset_info(self) -> None:
        """Test getting preset metadata."""
        preset_manager = PresetManager()

        # Save a preset
        config = {"author": "Test"}
        preset_manager.save_preset("Test Preset", config)

        # Get info
        info = preset_manager.get_preset_info("Test Preset")

        assert info["name"] == "Test Preset"
        assert info["schema_version"] == "1.0.0"
        assert "created_at" in info
        assert "config" not in info  # Config should be excluded

    def test_get_preset_path(self) -> None:
        """Test getting preset file path."""
        preset_manager = PresetManager()

        path = preset_manager.get_preset_path("Test Preset")
        expected_path = self.presets_dir / "test-preset.json"
        assert path == expected_path

    def test_clear_cache(self) -> None:
        """Test clearing preset list cache."""
        preset_manager = PresetManager()

        # Populate cache
        preset_manager.save_preset("Test", {"author": "Test"})
        preset_manager.list_presets()

        # Cache should be populated
        assert preset_manager._preset_cache is not None

        # Clear cache
        preset_manager.clear_cache()
        assert preset_manager._preset_cache is None

    def test_validate_preset_file(self) -> None:
        """Test validating preset files."""
        preset_manager = PresetManager()

        # Create valid preset
        preset_manager.save_preset("Valid", {"author": "Test"})
        valid_path = preset_manager.get_preset_path("Valid")
        assert preset_manager.validate_preset_file(valid_path)

        # Create invalid preset
        invalid_path = self.presets_dir / "invalid.json"
        with open(invalid_path, "w", encoding="utf-8") as f:
            json.dump({"invalid": "structure"}, f)

        assert not preset_manager.validate_preset_file(invalid_path)

    def test_name_sanitization(self) -> None:
        """Test preset name sanitization for filenames."""
        preset_manager = PresetManager()

        # Test various special characters
        test_cases = [
            ("My Preset", "my-preset.json"),
            ("Test/Preset", "testpreset.json"),  # "/" is removed, not replaced with hyphen
            ("Preset With Spaces", "preset-with-spaces.json"),
            ("Special!@#$%Characters", "specialcharacters.json"),  # Special chars are removed
            ("Multiple---Hyphens", "multiple-hyphens.json"),
        ]

        for name, expected_filename in test_cases:
            preset_manager.save_preset(name, {"author": "Test"})
            expected_path = self.presets_dir / expected_filename
            assert expected_path.exists(), f"Expected file {expected_filename} for name '{name}'"

    def test_unicode_handling(self) -> None:
        """Test handling of Unicode characters in preset names and content."""
        preset_manager = PresetManager()

        # Unicode in name and content
        config = {"author": "Tëst Authör", "license": "MIT", "pack_name": "Ünïcödë Pack"}

        preset_manager.save_preset("Ünïcödë Preset", config)

        # Should be able to load back correctly
        loaded_config = preset_manager.load_preset("Ünïcödë Preset")
        assert loaded_config == config

    @patch("core.preset_manager.jsonschema.validate")
    def test_schema_validation_error(self, mock_validate: Mock) -> None:
        """Test handling of schema validation errors."""
        preset_manager = PresetManager()

        # Mock validation to raise error
        from jsonschema import ValidationError

        mock_validate.side_effect = ValidationError("Test validation error")

        with pytest.raises(PresetValidationError, match="validation failed"):
            preset_manager.save_preset("Test", {"author": "Test"})

    def test_atomic_write_behavior(self) -> None:
        """Test that writes are atomic (temp file + rename)."""
        preset_manager = PresetManager()

        # This is more of an integration test to ensure the atomic write pattern works
        # We can't easily test interruption, but we can verify the end result
        config = {"author": "Test"}
        preset_manager.save_preset("Atomic Test", config)

        # File should exist and be valid
        preset_file = self.presets_dir / "atomic-test.json"
        assert preset_file.exists()

        # Content should be valid JSON
        with open(preset_file, encoding="utf-8") as f:
            data = json.load(f)

        assert data["config"] == config
