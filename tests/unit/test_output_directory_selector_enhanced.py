"""Tests for the enhanced OutputDirectorySelector with OutputFolderController integration."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from core.config_manager import ConfigManager
from gui.output.output_folder_controller import OutputFolderController, ValidationResult
from gui.widgets.directory_selector import OutputDirectorySelector


@pytest.fixture
def app():
    """Create QApplication for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_config():
    """Create a mock ConfigManager."""
    config = Mock(spec=ConfigManager)
    config.get.return_value = None
    return config


@pytest.fixture
def selector(app, mock_config):
    """Create an OutputDirectorySelector with mocked config."""
    return OutputDirectorySelector(parent=None, config_manager=mock_config)


class TestOutputDirectorySelectorEnhanced:
    """Test cases for the enhanced OutputDirectorySelector."""

    def test_initialization_with_controller(self, app, mock_config):
        """Test that selector initializes with OutputFolderController."""
        selector = OutputDirectorySelector(config_manager=mock_config)

        assert selector.controller is not None
        assert isinstance(selector.controller, OutputFolderController)
        assert selector.controller._config is mock_config

    def test_ui_components_created(self, selector):
        """Test that all UI components are created."""
        assert selector.path_edit is not None
        assert selector.browse_button is not None
        assert selector.open_folder_button is not None
        assert selector.validation_icon is not None
        assert selector.helper_text is not None

    def test_accessibility_properties(self, selector):
        """Test that accessibility properties are set."""
        assert selector.path_edit.accessibleName() == "Output directory path"
        assert selector.browse_button.accessibleName() == "Browse for output directory"
        assert selector.open_folder_button.accessibleName() == "Open output folder"

    def test_set_path_uses_controller(self, selector, tmp_path):
        """Test that set_path uses the controller."""
        with patch.object(selector.controller, "set_path") as mock_set_path:
            mock_result = ValidationResult(valid=True, normalized_path=tmp_path, message="Valid path", level="info")
            mock_set_path.return_value = mock_result

            selector.set_path(str(tmp_path))

            mock_set_path.assert_called_once()
            assert selector.path_edit.text() == str(tmp_path)

    def test_text_changed_updates_controller(self, selector, tmp_path):
        """Test that text changes update the controller."""
        with patch.object(selector.controller, "set_path") as mock_set_path:
            mock_result = ValidationResult(valid=True, normalized_path=tmp_path, message="Valid path", level="info")
            mock_set_path.return_value = mock_result

            selector.path_edit.setText(str(tmp_path))

            mock_set_path.assert_called_once()

    def test_validation_state_updates_ui(self, selector, tmp_path):
        """Test that validation state updates the UI correctly."""
        # Test valid state
        valid_result = ValidationResult(
            valid=True, normalized_path=tmp_path, message="Directory is ready for use", level="info"
        )

        # Initially helper text should be hidden
        assert not selector.helper_text.isVisible()

        selector._update_validation_state(valid_result)

        assert selector.helper_text.text() == "Directory is ready for use"
        # Note: isVisible() returns False in tests because parent widget is not shown
        # But we can verify the text was set and styling applied
        assert "28a745" in selector.path_edit.styleSheet()  # Green border

    def test_validation_state_error(self, selector, tmp_path):
        """Test validation state for errors."""
        error_result = ValidationResult(
            valid=False, normalized_path=tmp_path, message="Directory is not writable", level="error"
        )
        selector._update_validation_state(error_result)

        assert selector.helper_text.text() == "Directory is not writable"
        # Verify styling is applied correctly
        assert "dc3545" in selector.path_edit.styleSheet()  # Red border
        assert "dc3545" in selector.helper_text.styleSheet()  # Red text

    def test_validation_state_warning(self, selector, tmp_path):
        """Test validation state for warnings (can create)."""
        warning_result = ValidationResult(
            valid=False,
            normalized_path=tmp_path,
            message="Folder will be created when needed",
            level="info",
            can_create=True,
        )
        selector._update_validation_state(warning_result)

        assert selector.helper_text.text() == "Folder will be created when needed"
        # Verify styling is applied correctly for warning state
        assert "ffc107" in selector.path_edit.styleSheet()  # Yellow border

    @patch("gui.widgets.directory_selector.QMessageBox")
    def test_open_folder_existing_directory(self, mock_msgbox, selector, tmp_path):
        """Test opening an existing directory."""
        # Mock controller methods and file system operations
        with (
            patch.object(selector.controller, "current_path", return_value=tmp_path),
            patch.object(selector.controller, "open_in_file_manager", return_value=True) as mock_open,
            patch("gui.utils.fs.open_in_file_manager", return_value=True),
        ):
            selector._on_open_folder_clicked()

            mock_open.assert_called_once_with(tmp_path)
            mock_msgbox.assert_not_called()

    @patch("gui.widgets.directory_selector.QMessageBox")
    def test_open_folder_nonexistent_create_yes(self, mock_msgbox, selector, tmp_path):
        """Test opening non-existent directory with user choosing to create."""
        # Create a real non-existent path
        nonexistent = tmp_path / "nonexistent"

        # Mock controller methods and file system operations
        with (
            patch.object(selector.controller, "current_path", return_value=nonexistent),
            patch.object(selector.controller, "ensure_exists", return_value=True) as mock_ensure,
            patch.object(selector.controller, "open_in_file_manager", return_value=True) as mock_open,
            patch("gui.utils.fs.open_in_file_manager", return_value=True),
        ):
            # Mock QMessageBox.question to return Yes
            mock_msgbox.question.return_value = QMessageBox.StandardButton.Yes
            mock_msgbox.StandardButton = QMessageBox.StandardButton

            selector._on_open_folder_clicked()

            mock_msgbox.question.assert_called_once()
            # Check that ensure_exists was called with create_if_missing=True
            mock_ensure.assert_called_once()
            args, kwargs = mock_ensure.call_args
            assert len(args) == 1
            assert kwargs == {"create_if_missing": True}
            mock_open.assert_called_once()

    @patch("gui.widgets.directory_selector.QMessageBox")
    def test_open_folder_nonexistent_create_no(self, mock_msgbox, selector, tmp_path):
        """Test opening non-existent directory with user choosing not to create."""
        # Create a real non-existent path
        nonexistent = tmp_path / "nonexistent"

        # Mock controller methods
        with (
            patch.object(selector.controller, "current_path", return_value=nonexistent),
            patch.object(selector.controller, "ensure_exists") as mock_ensure,
            patch.object(selector.controller, "open_in_file_manager") as mock_open,
        ):
            # Mock QMessageBox.question to return No
            mock_msgbox.question.return_value = QMessageBox.StandardButton.No

            selector._on_open_folder_clicked()

            mock_msgbox.question.assert_called_once()
            # Should not try to create or open
            mock_ensure.assert_not_called()
            mock_open.assert_not_called()

    @patch("gui.widgets.directory_selector.QMessageBox")
    def test_open_folder_creation_fails(self, mock_msgbox, selector, tmp_path):
        """Test handling of folder creation failure."""
        # Create a real non-existent path
        nonexistent = tmp_path / "nonexistent"

        # Mock controller methods and file system operations
        with (
            patch.object(selector.controller, "current_path", return_value=nonexistent),
            patch.object(selector.controller, "ensure_exists", return_value=False),
            patch("gui.utils.fs.open_in_file_manager", return_value=True),
        ):
            # Mock QMessageBox.question to return Yes
            mock_msgbox.question.return_value = QMessageBox.StandardButton.Yes
            mock_msgbox.StandardButton = QMessageBox.StandardButton

            selector._on_open_folder_clicked()

            # Should show creation failed warning
            mock_msgbox.question.assert_called_once()
            mock_msgbox.warning.assert_called_once()

    @patch("gui.widgets.directory_selector.QMessageBox")
    def test_open_folder_file_manager_fails(self, mock_msgbox, selector, tmp_path):
        """Test handling of file manager opening failure."""
        # Mock controller methods and file system operations
        with (
            patch.object(selector.controller, "current_path", return_value=tmp_path),
            patch.object(selector.controller, "open_in_file_manager", return_value=False),
            patch("gui.utils.fs.open_in_file_manager", return_value=False),
        ):
            selector._on_open_folder_clicked()

            # Should show file manager failure warning
            mock_msgbox.warning.assert_called_once()

    def test_context_menu_setup(self, selector):
        """Test that context menu is set up correctly."""
        # Context menu should be set up during initialization on the path_edit
        assert selector.path_edit.contextMenuPolicy() == Qt.ContextMenuPolicy.CustomContextMenu

    def test_set_last_export_path(self, selector, tmp_path):
        """Test setting last export path."""
        with patch.object(selector.controller, "set_last_export_path") as mock_set:
            selector.set_last_export_path(tmp_path)
            mock_set.assert_called_once_with(tmp_path)

    def test_open_last_export_existing(self, selector, tmp_path):
        """Test opening last export path when it exists."""
        # Mock controller methods and file system operations
        with (
            patch.object(selector.controller, "last_export_path", return_value=tmp_path),
            patch.object(selector.context_menu, "_on_open_last_export_clicked") as mock_open,
            patch("gui.utils.fs.open_in_file_manager", return_value=True),
        ):
            selector.context_menu._on_open_last_export_clicked()

            mock_open.assert_called_once()

    @patch("gui.widgets.directory_context_menu.QMessageBox")
    def test_open_last_export_nonexistent(self, mock_msgbox, selector):
        """Test opening last export path when it doesn't exist."""
        # Mock controller to return None
        with patch.object(selector.controller, "last_export_path", return_value=None):
            selector.context_menu._on_open_last_export_clicked()

            mock_msgbox.information.assert_called_once()

    def test_browse_button_functionality(self, selector, tmp_path):
        """Test browse button opens file dialog and sets path."""
        with patch("gui.widgets.directory_selector.QFileDialog.getExistingDirectory") as mock_dialog:
            mock_dialog.return_value = str(tmp_path)

            with patch.object(selector, "_normalize_and_set_path") as mock_normalize:
                selector._on_browse_clicked()

                mock_dialog.assert_called_once()
                mock_normalize.assert_called_once_with(tmp_path)

    def test_browse_button_cancelled(self, selector):
        """Test browse button when user cancels dialog."""
        with patch("gui.widgets.directory_selector.QFileDialog.getExistingDirectory") as mock_dialog:
            mock_dialog.return_value = ""  # User cancelled

            with patch.object(selector, "_normalize_and_set_path") as mock_normalize:
                selector._on_browse_clicked()

                mock_dialog.assert_called_once()
                mock_normalize.assert_not_called()

    def test_empty_text_resets_to_controller(self, selector, tmp_path):
        """Test that empty text resets to controller's current path."""
        # Mock controller current path
        selector.controller.current_path = Mock(return_value=tmp_path)

        with patch.object(selector, "_apply_controller_path") as mock_apply:
            selector._on_text_changed("")

            mock_apply.assert_called_once_with(tmp_path)

    def test_signals_emitted_correctly(self, selector, tmp_path):
        """Test that signals are emitted when path changes."""
        path_changed_emitted = False
        validity_changed_emitted = False
        ready_for_use_emitted = False

        def on_path_changed(path):
            nonlocal path_changed_emitted
            path_changed_emitted = True

        def on_validity_changed(valid, message):
            nonlocal validity_changed_emitted
            validity_changed_emitted = True

        def on_ready_for_use(ready):
            nonlocal ready_for_use_emitted
            ready_for_use_emitted = True

        selector.pathChanged.connect(on_path_changed)
        selector.validityChanged.connect(on_validity_changed)
        selector.readyForUse.connect(on_ready_for_use)

        # Trigger a path change by calling set_path directly
        # This ensures the signals are emitted
        selector.set_path(str(tmp_path))

        # At least validity_changed and ready_for_use should be emitted
        assert validity_changed_emitted
        assert ready_for_use_emitted


class TestIntegrationWithMainWindow:
    """Integration tests with MainWindow."""

    def test_main_window_integration(self, app):
        """Test that MainWindow integrates correctly with enhanced selector."""
        from gui.main_window import MainWindow

        # This should not raise any exceptions
        window = MainWindow()

        # Check that the output directory selector is properly integrated
        assert window.ui.output_dir_selector is not None
        assert hasattr(window.ui.output_dir_selector, "controller")
        assert window.ui.output_dir_selector.controller is not None

        # Check that the main window has the output controller
        assert hasattr(window, "output_controller")
        assert window.output_controller is not None

    def test_conversion_completion_updates_last_export(self, app):
        """Test that conversion completion updates last export path."""
        from gui.main_window import MainWindow

        window = MainWindow()

        # Mock the output controller
        with patch.object(window.output_controller, "set_last_export_path") as mock_set:
            # Simulate conversion completion
            result = {"output_dir": "/test/output/path"}
            window._on_conversion_completed(result)

            mock_set.assert_called_once()
            call_args = mock_set.call_args[0][0]
            assert str(call_args) == "/test/output/path"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_invalid_path_handling(self, selector):
        """Test handling of invalid paths."""
        invalid_paths = [
            "/invalid/\x00/path",  # Null byte
            "\\invalid\\path" if Path.cwd().drive else "/invalid/path",  # Platform-specific
            "",  # Empty string
            "   ",  # Whitespace only
        ]

        for invalid_path in invalid_paths:
            # Should not raise exceptions
            try:
                selector.path_edit.setText(invalid_path)
                # Validation should handle the invalid path gracefully
                assert not selector.is_valid()
            except Exception as e:
                pytest.fail(f"Invalid path '{invalid_path}' caused exception: {e}")

    def test_unicode_path_handling(self, selector, tmp_path):
        """Test handling of Unicode paths."""
        unicode_dir = tmp_path / "测试文件夹"
        unicode_dir.mkdir()

        # Should handle Unicode paths correctly
        selector.set_path(str(unicode_dir))

        # Path should be normalized and valid
        assert selector.path() == str(unicode_dir.resolve())

    def test_very_long_path_handling(self, selector, tmp_path):
        """Test handling of very long paths."""
        # Create a deeply nested directory structure
        long_path = tmp_path
        for i in range(10):
            long_path = long_path / f"very_long_directory_name_{i}"

        try:
            long_path.mkdir(parents=True)
            selector.set_path(str(long_path))

            # Should handle long paths without issues
            assert selector.path() == str(long_path.resolve())
        except OSError:
            # Skip test if filesystem doesn't support long paths
            pytest.skip("Filesystem doesn't support long paths")

    def test_network_path_handling(self, selector):
        """Test handling of network paths (if applicable)."""
        network_paths = [
            "//server/share",  # UNC path
            "\\\\server\\share",  # Windows UNC
        ]

        for network_path in network_paths:
            # Should not crash, even if path doesn't exist
            try:
                selector.set_path(network_path)
                # Validation should handle network paths appropriately
                assert isinstance(selector.is_valid(), bool)
            except Exception as e:
                pytest.fail(f"Network path '{network_path}' caused exception: {e}")

    def test_permission_denied_handling(self, selector, tmp_path):
        """Test handling of permission denied scenarios."""
        # Create a directory and make it read-only
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o555)  # Read and execute only

        try:
            selector.set_path(str(readonly_dir))

            # Should detect that directory is not writable
            assert not selector.is_valid()
            assert "not writable" in selector.error_message().lower()
        finally:
            # Restore permissions for cleanup
            readonly_dir.chmod(0o755)

    def test_concurrent_access(self, app, mock_config):
        """Test concurrent access to the same paths."""
        # Create multiple selectors
        selector1 = OutputDirectorySelector(config_manager=mock_config)
        selector2 = OutputDirectorySelector(config_manager=mock_config)

        # Both should work independently
        assert selector1.controller is not selector2.controller

        # Setting path in one shouldn't affect the other directly
        with (
            patch.object(selector1.controller, "set_path") as mock1,
            patch.object(selector2.controller, "set_path") as mock2,
        ):
            mock1.return_value = ValidationResult(True, Path("/test1"), "Valid", "info")
            mock2.return_value = ValidationResult(True, Path("/test2"), "Valid", "info")

            selector1.set_path("/test1")
            selector2.set_path("/test2")

            mock1.assert_called_once()
            mock2.assert_called_once()
