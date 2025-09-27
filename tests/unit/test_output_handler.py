"""
Tests for the OutputHandler class.

This module tests output folder handling functionality including
directory selection, validation, and opening folders in the file manager.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication

from gui.handlers.output_handler import OutputHandler


class TestOutputHandler:
    """Test cases for OutputHandler."""

    def setup_method(self):
        """Set up test fixtures."""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()

        # Create a mock main window
        self.mock_main_window = Mock()
        self.mock_main_window.config_manager = Mock()
        self.mock_main_window.ui_state_handler = Mock()
        self.mock_main_window.ui = Mock()

        # Create handler instance
        self.handler = OutputHandler(self.mock_main_window)

    def teardown_method(self):
        """Clean up after tests."""
        if hasattr(self, "app") and self.app:
            self.app.quit()


class TestOutputDirectoryHandling(TestOutputHandler):
    """Test output directory handling methods."""

    def test_on_output_dir_changed(self):
        """Test output directory change handling."""
        test_path = "/test/output/path"

        self.handler.on_output_dir_changed(test_path)

        self.mock_main_window.config_manager.set.assert_called_once_with("conversion/outputDirectory", test_path)

    def test_on_output_dir_validity_changed(self):
        """Test output directory validity change handling."""
        self.handler.on_output_dir_validity_changed(True, "")

        self.mock_main_window.ui_state_handler._update_convert_button_state.assert_called_once()

    def test_on_output_dir_validity_changed_invalid(self):
        """Test output directory validity change handling with invalid state."""
        self.handler.on_output_dir_validity_changed(False, "Invalid path")

        self.mock_main_window.ui_state_handler._update_convert_button_state.assert_called_once()


class TestOpenOutputFolder(TestOutputHandler):
    """Test opening output folder functionality."""

    def test_on_open_output_clicked_no_selector(self):
        """Test open output folder when selector is not available."""
        self.mock_main_window.ui.output_dir_selector = None

        with patch.object(self.handler, "_show_output_error") as mock_show_error:
            self.handler.on_open_output_clicked()
            mock_show_error.assert_called_once_with("Output directory selector not available")

    def test_on_open_output_clicked_no_path(self):
        """Test open output folder when no path is selected."""
        self.mock_main_window.ui.output_dir_selector = Mock()
        self.mock_main_window.ui.output_dir_selector.path.return_value = ""

        with patch.object(self.handler, "_show_output_error") as mock_show_error:
            self.handler.on_open_output_clicked()
            mock_show_error.assert_called_once_with("No output directory selected")

    def test_on_open_output_clicked_invalid_path(self):
        """Test open output folder with invalid path."""
        self.mock_main_window.ui.output_dir_selector = Mock()
        self.mock_main_window.ui.output_dir_selector.path.return_value = "/invalid/path"

        with (
            patch("pathlib.Path.resolve", side_effect=OSError("Invalid path")),
            patch.object(self.handler, "_show_output_error") as mock_show_error,
        ):
            self.handler.on_open_output_clicked()
            mock_show_error.assert_called_once_with("Invalid output path: Invalid path")

    def test_on_open_output_clicked_creates_directory(self):
        """Test open output folder creates directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_dir = Path(temp_dir) / "new_directory"

            self.mock_main_window.ui.output_dir_selector = Mock()
            self.mock_main_window.ui.output_dir_selector.path.return_value = str(nonexistent_dir)

            with patch.object(self.handler, "_open_folder_with_system", return_value=True):
                self.handler.on_open_output_clicked()

                # Directory should have been created
                assert nonexistent_dir.exists()
                assert nonexistent_dir.is_dir()

    def test_on_open_output_clicked_directory_creation_fails(self):
        """Test open output folder when directory creation fails."""
        self.mock_main_window.ui.output_dir_selector = Mock()
        self.mock_main_window.ui.output_dir_selector.path.return_value = "/invalid/path"

        with patch("pathlib.Path.resolve") as mock_resolve:
            mock_path = Mock()
            mock_path.exists.return_value = False
            mock_path.mkdir.side_effect = PermissionError("Permission denied")
            mock_resolve.return_value = mock_path

            with patch.object(self.handler, "_show_output_error") as mock_show_error:
                self.handler.on_open_output_clicked()
                mock_show_error.assert_called_once_with("Cannot create output directory: Permission denied")

    def test_on_open_output_clicked_path_not_directory(self):
        """Test open output folder when path exists but is not a directory."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            try:
                self.mock_main_window.ui.output_dir_selector = Mock()
                self.mock_main_window.ui.output_dir_selector.path.return_value = temp_file.name

                with patch.object(self.handler, "_show_output_error") as mock_show_error:
                    self.handler.on_open_output_clicked()
                    # Use the resolved path for comparison
                    expected_path = str(Path(temp_file.name).resolve())
                    mock_show_error.assert_called_once_with(f"Path is not a directory: {expected_path}")
            finally:
                os.unlink(temp_file.name)

    def test_on_open_output_clicked_no_access(self):
        """Test open output folder when directory is not accessible."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_main_window.ui.output_dir_selector = Mock()
            self.mock_main_window.ui.output_dir_selector.path.return_value = temp_dir

            with (
                patch("os.access", return_value=False),
                patch.object(self.handler, "_show_output_error") as mock_show_error,
            ):
                self.handler.on_open_output_clicked()
                # Use the resolved path for comparison
                expected_path = str(Path(temp_dir).resolve())
                mock_show_error.assert_called_once_with(f"Cannot access output directory: {expected_path}")

    def test_on_open_output_clicked_success(self):
        """Test successful open output folder operation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_main_window.ui.output_dir_selector = Mock()
            self.mock_main_window.ui.output_dir_selector.path.return_value = temp_dir

            with patch.object(self.handler, "_open_folder_with_system", return_value=True):
                self.handler.on_open_output_clicked()
                # Should not show any error

    def test_on_open_output_clicked_open_fails(self):
        """Test open output folder when opening fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_main_window.ui.output_dir_selector = Mock()
            self.mock_main_window.ui.output_dir_selector.path.return_value = temp_dir

            with (
                patch.object(self.handler, "_open_folder_with_system", return_value=False),
                patch.object(self.handler, "_show_output_error") as mock_show_error,
            ):
                self.handler.on_open_output_clicked()
                # Use the resolved path for comparison
                expected_path = str(Path(temp_dir).resolve())
                mock_show_error.assert_called_once_with(f"Failed to open folder: {expected_path}")


class TestOpenFolderWithSystem(TestOutputHandler):
    """Test system folder opening functionality."""

    def test_open_folder_qt_success(self):
        """Test successful folder opening via Qt."""
        test_path = Path("/test/path")

        with patch("PySide6.QtGui.QDesktopServices.openUrl", return_value=True) as mock_open:
            result = self.handler._open_folder_with_system(test_path)

            assert result is True
            mock_open.assert_called_once()
            # Check that QUrl.fromLocalFile was called with the path
            call_args = mock_open.call_args[0][0]
            assert isinstance(call_args, QUrl)

    def test_open_folder_windows_fallback(self):
        """Test folder opening fallback on Windows."""
        test_path = Path("/test/path")

        with (
            patch("PySide6.QtGui.QDesktopServices.openUrl", return_value=False),
            patch("platform.system", return_value="Windows"),
            patch("subprocess.run") as mock_run,
        ):
            result = self.handler._open_folder_with_system(test_path)

            assert result is True
            mock_run.assert_called_once_with(["explorer", str(test_path)], check=True)

    def test_open_folder_macos_fallback(self):
        """Test folder opening fallback on macOS."""
        test_path = Path("/test/path")

        with (
            patch("PySide6.QtGui.QDesktopServices.openUrl", return_value=False),
            patch("platform.system", return_value="Darwin"),
            patch("subprocess.run") as mock_run,
        ):
            result = self.handler._open_folder_with_system(test_path)

            assert result is True
            mock_run.assert_called_once_with(["open", str(test_path)], check=True)

    def test_open_folder_linux_fallback_success(self):
        """Test folder opening fallback on Linux with successful command."""
        test_path = Path("/test/path")

        with (
            patch("PySide6.QtGui.QDesktopServices.openUrl", return_value=False),
            patch("platform.system", return_value="Linux"),
            patch("subprocess.run") as mock_run,
        ):
            result = self.handler._open_folder_with_system(test_path)

            assert result is True
            mock_run.assert_called_once_with(["xdg-open", str(test_path)], check=True)

    def test_open_folder_linux_fallback_multiple_attempts(self):
        """Test folder opening fallback on Linux with multiple command attempts."""
        test_path = Path("/test/path")

        with (
            patch("PySide6.QtGui.QDesktopServices.openUrl", return_value=False),
            patch("platform.system", return_value="Linux"),
            patch("subprocess.run") as mock_run,
        ):
            # First command fails, second succeeds
            mock_run.side_effect = [
                subprocess.CalledProcessError(1, "xdg-open"),
                None,  # Success for nautilus
            ]

            result = self.handler._open_folder_with_system(test_path)

            assert result is True
            assert mock_run.call_count == 2
            mock_run.assert_any_call(["xdg-open", str(test_path)], check=True)
            mock_run.assert_any_call(["nautilus", str(test_path)], check=True)

    def test_open_folder_linux_all_commands_fail(self):
        """Test folder opening fallback on Linux when all commands fail."""
        test_path = Path("/test/path")

        with (
            patch("PySide6.QtGui.QDesktopServices.openUrl", return_value=False),
            patch("platform.system", return_value="Linux"),
            patch("subprocess.run", side_effect=FileNotFoundError("Command not found")),
        ):
            # Create a mock that simulates the recursive behavior
            call_count = 0

            def mock_open_folder(path):
                nonlocal call_count
                call_count += 1

                if call_count == 1:
                    # First call (original path) - simulate all commands failing
                    # This will trigger the recursive call to parent
                    if path.parent != path:
                        return mock_open_folder(path.parent)
                    return False
                else:
                    # Second call (parent path) - simulate success
                    return True

            with patch.object(self.handler, "_open_folder_with_system", side_effect=mock_open_folder):
                result = self.handler._open_folder_with_system(test_path)
                assert result is True
                assert call_count == 2

    def test_open_folder_linux_parent_recursion_fails(self):
        """Test folder opening when parent directory recursion also fails."""
        # Use root path where parent == self
        test_path = Path("/")

        with (
            patch("PySide6.QtGui.QDesktopServices.openUrl", return_value=False),
            patch("platform.system", return_value="Linux"),
            patch("subprocess.run", side_effect=FileNotFoundError("Command not found")),
        ):
            result = self.handler._open_folder_with_system(test_path)
            assert result is False

    def test_open_folder_subprocess_error(self):
        """Test folder opening when subprocess raises an error."""
        test_path = Path("/test/path")

        with (
            patch("PySide6.QtGui.QDesktopServices.openUrl", return_value=False),
            patch("platform.system", return_value="Windows"),
            patch("subprocess.run", side_effect=OSError("System error")),
        ):
            result = self.handler._open_folder_with_system(test_path)
            assert result is False


class TestShowOutputError(TestOutputHandler):
    """Test error display functionality."""

    def test_show_output_error(self):
        """Test showing output error message."""
        test_message = "Test error message"

        with patch("PySide6.QtWidgets.QMessageBox.warning") as mock_warning:
            self.handler._show_output_error(test_message)

            mock_warning.assert_called_once_with(self.mock_main_window, "Output Folder Error", test_message)


class TestIntegration(TestOutputHandler):
    """Test integration scenarios."""

    def test_full_workflow_success(self):
        """Test complete successful workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_main_window.ui.output_dir_selector = Mock()
            self.mock_main_window.ui.output_dir_selector.path.return_value = temp_dir

            with patch.object(self.handler, "_open_folder_with_system", return_value=True):
                # Should complete without errors
                self.handler.on_open_output_clicked()

    def test_full_workflow_with_directory_creation(self):
        """Test workflow that requires directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = Path(temp_dir) / "new_output"

            self.mock_main_window.ui.output_dir_selector = Mock()
            self.mock_main_window.ui.output_dir_selector.path.return_value = str(new_dir)

            with patch.object(self.handler, "_open_folder_with_system", return_value=True):
                self.handler.on_open_output_clicked()

                # Directory should have been created
                assert new_dir.exists()
                assert new_dir.is_dir()
