"""Tests for the OutputFolderController class."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from core.config_manager import ConfigManager
from gui.output.output_folder_controller import OutputFolderController, ValidationResult


class TestValidationResult:
    """Test cases for the ValidationResult dataclass."""

    def test_validation_result_creation(self):
        """Test creating a ValidationResult with all fields."""
        result = ValidationResult(
            valid=True,
            normalized_path=Path("/test/path"),
            message="Test message",
            level="info",
            can_create=True,
            writable=True,
        )

        assert result.valid is True
        assert result.normalized_path == Path("/test/path")
        assert result.message == "Test message"
        assert result.level == "info"
        assert result.can_create is True
        assert result.writable is True

    def test_validation_result_defaults(self):
        """Test ValidationResult with default values."""
        result = ValidationResult(valid=False, normalized_path=Path("/test/path"), message="Error message", level="error")

        assert result.valid is False
        assert result.can_create is False  # Default
        assert result.writable is False  # Default


class TestOutputFolderController:
    """Test cases for the OutputFolderController class."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock ConfigManager for testing."""
        config = Mock(spec=ConfigManager)
        config.get.return_value = None
        return config

    @pytest.fixture
    def controller(self, mock_config):
        """Create an OutputFolderController with mocked config."""
        return OutputFolderController(mock_config)

    def test_init_with_config_manager(self, mock_config):
        """Test initialization with provided ConfigManager."""
        controller = OutputFolderController(mock_config)
        assert controller._config is mock_config

    def test_init_without_config_manager(self):
        """Test initialization without ConfigManager creates one."""
        with patch("gui.output.output_folder_controller.ConfigManager") as mock_cm_class:
            mock_cm = Mock()
            mock_cm_class.return_value = mock_cm
            mock_cm.get.return_value = None

            controller = OutputFolderController()
            assert controller._config is mock_cm
            mock_cm_class.assert_called_once()

    def test_load_current_path_from_config(self, mock_config, tmp_path):
        """Test loading current path from configuration."""
        mock_config.get.return_value = str(tmp_path)

        controller = OutputFolderController(mock_config)

        assert controller._current_path == tmp_path.resolve()
        mock_config.get.assert_called_with("paths/output_dir")

    def test_load_current_path_invalid_stored_path(self, mock_config):
        """Test handling of invalid stored path."""
        mock_config.get.return_value = "/invalid/\x00/path"

        with patch.object(OutputFolderController, "default_path", return_value=Path("/default")):
            controller = OutputFolderController(mock_config)
            # Should fall back to default path
            assert controller._current_path == Path("/default")

    def test_load_current_path_no_stored_path(self, mock_config):
        """Test behavior when no path is stored."""
        mock_config.get.return_value = None

        with patch.object(OutputFolderController, "default_path", return_value=Path("/default")):
            controller = OutputFolderController(mock_config)
            assert controller._current_path == Path("/default")

    def test_current_path_returns_loaded_path(self, controller, tmp_path):
        """Test that current_path returns the loaded path."""
        controller._current_path = tmp_path
        assert controller.current_path() == tmp_path

    def test_current_path_falls_back_to_default(self, controller):
        """Test that current_path falls back to default when none set."""
        controller._current_path = None

        with patch.object(controller, "default_path", return_value=Path("/default")) as mock_default:
            result = controller.current_path()
            assert result == Path("/default")
            mock_default.assert_called_once()

    @patch("gui.output.output_folder_controller.QStandardPaths.writableLocation")
    def test_default_path_computation(self, mock_writable_location, mock_config):
        """Test default path computation from Documents directory."""
        mock_writable_location.return_value = "/home/user/Documents"
        mock_config.get.return_value = None  # No stored default

        controller = OutputFolderController(mock_config)
        default = controller.default_path()

        expected = Path("/home/user/Documents/pdf2foundry")
        assert default == expected
        mock_config.set.assert_called_with("paths/default_output_dir", str(expected))

    @patch("gui.output.output_folder_controller.QStandardPaths.writableLocation")
    def test_default_path_fallback_to_cwd(self, mock_writable_location, mock_config):
        """Test default path fallback to current working directory."""
        mock_writable_location.return_value = None  # No Documents directory
        mock_config.get.return_value = None

        with patch("pathlib.Path.cwd", return_value=Path("/current/dir")):
            controller = OutputFolderController(mock_config)
            default = controller.default_path()

            expected = Path("/current/dir/pdf2foundry")
            assert default == expected

    def test_default_path_uses_stored_default(self, mock_config, tmp_path):
        """Test that stored default path is used when available."""
        stored_default = str(tmp_path / "stored_default")
        mock_config.get.return_value = stored_default

        controller = OutputFolderController(mock_config)
        default = controller.default_path()

        assert default == Path(stored_default).resolve()

    def test_set_path_valid_directory(self, controller, tmp_path):
        """Test setting a valid directory path."""
        result = controller.set_path(tmp_path, "user")

        assert result.valid is True
        assert result.normalized_path == tmp_path.resolve()
        assert result.writable is True
        assert controller._current_path == tmp_path.resolve()
        controller._config.set.assert_called_with("paths/output_dir", str(tmp_path.resolve()))

    def test_set_path_invalid_path(self, controller):
        """Test setting an invalid path."""
        invalid_path = Path("/invalid/\x00/path")

        result = controller.set_path(invalid_path, "user")

        assert result.valid is False
        assert result.level == "error"
        assert "Invalid path" in result.message

    def test_set_path_nonexistent_creatable(self, controller, tmp_path):
        """Test setting a non-existent but creatable path."""
        new_dir = tmp_path / "new_directory"

        result = controller.set_path(new_dir, "user")

        assert result.valid is False  # Doesn't exist yet
        assert result.can_create is True
        assert result.level == "info"
        assert "will be created" in result.message
        assert controller._current_path == new_dir.resolve()

    def test_set_path_file_not_directory(self, controller, tmp_path):
        """Test setting a path that points to a file."""
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("test")

        result = controller.set_path(test_file, "user")

        assert result.valid is False
        assert result.level == "error"
        assert "not a directory" in result.message

    def test_reset_to_default(self, controller):
        """Test resetting to default path."""
        default_path = Path("/default/path")

        with (
            patch.object(controller, "default_path", return_value=default_path),
            patch.object(controller, "set_path") as mock_set_path,
        ):
            mock_result = ValidationResult(True, default_path, "Reset", "info")
            mock_set_path.return_value = mock_result

            result = controller.reset_to_default()

            mock_set_path.assert_called_once_with(default_path, "reset")
            assert result is mock_result

    def test_ensure_exists_existing_directory(self, controller, tmp_path):
        """Test ensure_exists with existing directory."""
        result = controller.ensure_exists(tmp_path)
        assert result is True

    def test_ensure_exists_existing_file(self, controller, tmp_path):
        """Test ensure_exists with existing file (should fail)."""
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("test")

        result = controller.ensure_exists(test_file)
        assert result is False

    def test_ensure_exists_create_directory(self, controller, tmp_path):
        """Test ensure_exists creating a new directory."""
        new_dir = tmp_path / "new_directory"

        result = controller.ensure_exists(new_dir, create_if_missing=True)

        assert result is True
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_ensure_exists_no_create(self, controller, tmp_path):
        """Test ensure_exists without creating missing directory."""
        new_dir = tmp_path / "new_directory"

        result = controller.ensure_exists(new_dir, create_if_missing=False)

        assert result is False
        assert not new_dir.exists()

    def test_ensure_exists_creation_failure(self, controller, tmp_path):
        """Test ensure_exists when directory creation fails."""
        new_dir = tmp_path / "new_directory"

        with patch.object(Path, "mkdir", side_effect=PermissionError("Access denied")):
            result = controller.ensure_exists(new_dir, create_if_missing=True)

            assert result is False

    def test_is_writable_existing_writable_directory(self, controller, tmp_path):
        """Test is_writable with writable directory."""
        result = controller.is_writable(tmp_path)
        assert result is True

    def test_is_writable_nonexistent_path(self, controller, tmp_path):
        """Test is_writable with non-existent path."""
        nonexistent = tmp_path / "does_not_exist"
        result = controller.is_writable(nonexistent)
        assert result is False

    def test_is_writable_file_path(self, controller, tmp_path):
        """Test is_writable with file path."""
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("test")

        result = controller.is_writable(test_file)
        assert result is False

    def test_is_writable_tempfile_creation_fails(self, controller, tmp_path):
        """Test is_writable when temporary file creation fails."""
        with (
            patch("tempfile.NamedTemporaryFile", side_effect=PermissionError("Access denied")),
            patch("os.access", return_value=True),
        ):
            result = controller.is_writable(tmp_path)
            assert result is True  # Falls back to os.access

    def test_is_writable_all_methods_fail(self, controller, tmp_path):
        """Test is_writable when all methods fail."""
        with (
            patch("tempfile.NamedTemporaryFile", side_effect=PermissionError("Access denied")),
            patch("os.access", side_effect=OSError("Access check failed")),
        ):
            result = controller.is_writable(tmp_path)
            assert result is False

    @patch("gui.output.output_folder_controller.open_in_file_manager")
    def test_open_in_file_manager(self, mock_open_fm, controller, tmp_path):
        """Test opening directory in file manager."""
        mock_open_fm.return_value = True

        result = controller.open_in_file_manager(tmp_path)

        assert result is True
        mock_open_fm.assert_called_once_with(tmp_path)

    def test_last_export_path_none_stored(self, controller):
        """Test last_export_path when none is stored."""
        controller._config.get.return_value = None

        result = controller.last_export_path()
        assert result is None

    def test_last_export_path_valid_stored(self, controller, tmp_path):
        """Test last_export_path with valid stored path."""
        controller._config.get.return_value = str(tmp_path)

        result = controller.last_export_path()
        assert result == tmp_path.resolve()

    def test_last_export_path_invalid_stored(self, controller):
        """Test last_export_path with invalid stored path."""
        controller._config.get.return_value = "/invalid/\x00/path"

        result = controller.last_export_path()
        assert result is None

    def test_set_last_export_path(self, controller, tmp_path):
        """Test setting last export path."""
        controller.set_last_export_path(tmp_path)

        controller._config.set.assert_called_with("paths/last_export_dir", str(tmp_path.resolve()))

    def test_set_last_export_path_invalid(self, controller):
        """Test setting invalid last export path."""
        invalid_path = Path("/invalid/\x00/path")

        # Reset the mock to ignore calls from initialization
        controller._config.set.reset_mock()

        # Should not raise exception, just log warning
        controller.set_last_export_path(invalid_path)

        # Config.set should not be called for invalid paths
        controller._config.set.assert_not_called()

    def test_validate_path_nonexistent_creatable(self, controller, tmp_path):
        """Test path validation for non-existent but creatable path."""
        new_dir = tmp_path / "new_directory"

        result = controller._validate_path(new_dir)

        assert result.valid is False
        assert result.can_create is True
        assert result.level == "info"
        assert "will be created" in result.message

    def test_validate_path_nonexistent_not_creatable(self, controller, tmp_path):
        """Test path validation for non-existent, non-creatable path."""
        # Create a read-only parent directory
        readonly_parent = tmp_path / "readonly"
        readonly_parent.mkdir()
        readonly_parent.chmod(0o555)  # Read and execute only

        new_dir = readonly_parent / "new_directory"

        try:
            result = controller._validate_path(new_dir)

            assert result.valid is False
            assert result.can_create is False
            assert result.level == "error"
            assert "not writable" in result.message
        finally:
            # Restore permissions for cleanup
            readonly_parent.chmod(0o755)

    def test_validate_path_invalid_parent(self, controller, tmp_path):
        """Test path validation with invalid parent."""
        # Create a path with non-existent parent
        invalid_path = tmp_path / "nonexistent_parent" / "new_directory"

        result = controller._validate_path(invalid_path)

        assert result.valid is False
        assert result.can_create is False
        assert result.level == "error"
        assert "invalid" in result.message.lower() or "does not exist" in result.message

    def test_validate_path_file_not_directory(self, controller, tmp_path):
        """Test path validation for existing file."""
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("test")

        result = controller._validate_path(test_file)

        assert result.valid is False
        assert result.can_create is False
        assert result.level == "error"
        assert "not a directory" in result.message

    def test_validate_path_readonly_directory(self, controller, tmp_path):
        """Test path validation for read-only directory."""
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o555)  # Read and execute only

        try:
            result = controller._validate_path(readonly_dir)

            assert result.valid is False
            assert result.can_create is False
            assert result.level == "error"
            assert "not writable" in result.message
        finally:
            # Restore permissions for cleanup
            readonly_dir.chmod(0o755)

    def test_validate_path_valid_directory(self, controller, tmp_path):
        """Test path validation for valid writable directory."""
        result = controller._validate_path(tmp_path)

        assert result.valid is True
        assert result.can_create is True
        assert result.writable is True
        assert result.level == "info"
        assert "ready for use" in result.message


class TestIntegration:
    """Integration tests for OutputFolderController."""

    def test_full_workflow_with_real_config(self, tmp_path):
        """Test complete workflow with real ConfigManager."""
        # Use a temporary directory for QSettings
        with patch("core.config_manager.QSettings") as mock_qsettings_class:
            mock_qsettings = Mock()
            mock_qsettings_class.return_value = mock_qsettings
            mock_qsettings.value.return_value = None

            # Create controller with real ConfigManager
            from core.config_manager import ConfigManager

            config = ConfigManager()
            controller = OutputFolderController(config)

            # Set a path
            test_dir = tmp_path / "test_output"
            result = controller.set_path(test_dir, "user")

            # Verify the path was set and persisted
            assert result.can_create is True
            assert controller.current_path() == test_dir.resolve()

            # Create the directory and verify it becomes valid
            test_dir.mkdir()
            result = controller._validate_path(test_dir)
            assert result.valid is True

    def test_path_normalization_edge_cases(self, tmp_path):
        """Test path normalization with various edge cases."""
        controller = OutputFolderController()

        # Test with relative path
        relative_path = Path("./relative/path")
        result = controller.set_path(relative_path, "user")
        assert result.normalized_path.is_absolute()

        # Test with user home expansion
        home_path = Path("~/test_output")
        result = controller.set_path(home_path, "user")
        assert "~" not in str(result.normalized_path)
        assert result.normalized_path.is_absolute()

    def test_concurrent_access_safety(self, tmp_path):
        """Test that multiple controller instances don't interfere."""
        # Create two controllers
        controller1 = OutputFolderController()
        controller2 = OutputFolderController()

        # Set different paths
        path1 = tmp_path / "controller1"
        path2 = tmp_path / "controller2"

        controller1.set_path(path1, "user")
        controller2.set_path(path2, "user")

        # Each should maintain its own current path
        assert controller1.current_path() == path1.resolve()
        assert controller2.current_path() == path2.resolve()
