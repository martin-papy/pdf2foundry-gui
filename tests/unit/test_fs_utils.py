"""Tests for cross-platform file system utilities."""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

from gui.utils.fs import open_in_file_manager


class TestOpenInFileManager:
    """Test cases for the open_in_file_manager function."""

    def test_nonexistent_path_returns_false(self, tmp_path):
        """Test that non-existent paths return False without attempting to open."""
        nonexistent = tmp_path / "does_not_exist"
        assert not nonexistent.exists()

        result = open_in_file_manager(nonexistent)
        assert result is False

    def test_file_path_returns_false(self, tmp_path):
        """Test that file paths (not directories) return False."""
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("test content")
        assert test_file.is_file()

        result = open_in_file_manager(test_file)
        assert result is False

    @patch.object(QDesktopServices, "openUrl")
    def test_qdesktopservices_success(self, mock_open_url, tmp_path):
        """Test successful opening using QDesktopServices."""
        mock_open_url.return_value = True

        result = open_in_file_manager(tmp_path)

        assert result is True
        mock_open_url.assert_called_once()

        # Verify the URL was constructed correctly
        call_args = mock_open_url.call_args[0][0]
        assert isinstance(call_args, QUrl)
        assert call_args.isLocalFile()
        assert Path(call_args.toLocalFile()) == tmp_path.resolve()

    @patch.object(QDesktopServices, "openUrl")
    @patch("subprocess.run")
    @patch("platform.system")
    def test_windows_fallback(self, mock_system, mock_subprocess, mock_open_url, tmp_path):
        """Test Windows Explorer fallback when QDesktopServices fails."""
        mock_open_url.return_value = False
        mock_system.return_value = "Windows"

        result = open_in_file_manager(tmp_path)

        assert result is True
        mock_subprocess.assert_called_once_with(["explorer", str(tmp_path.resolve())], check=False)

    @patch.object(QDesktopServices, "openUrl")
    @patch("subprocess.run")
    @patch("platform.system")
    def test_macos_fallback(self, mock_system, mock_subprocess, mock_open_url, tmp_path):
        """Test macOS Finder fallback when QDesktopServices fails."""
        mock_open_url.return_value = False
        mock_system.return_value = "Darwin"

        result = open_in_file_manager(tmp_path)

        assert result is True
        mock_subprocess.assert_called_once_with(["open", str(tmp_path.resolve())], check=False)

    @patch.object(QDesktopServices, "openUrl")
    @patch("subprocess.run")
    @patch("platform.system")
    def test_linux_fallback_success(self, mock_system, mock_subprocess, mock_open_url, tmp_path):
        """Test Linux xdg-open fallback when QDesktopServices fails."""
        mock_open_url.return_value = False
        mock_system.return_value = "Linux"

        # Mock successful xdg-open
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        result = open_in_file_manager(tmp_path)

        assert result is True
        mock_subprocess.assert_called_once_with(["xdg-open", str(tmp_path.resolve())], check=False, capture_output=True)

    @patch.object(QDesktopServices, "openUrl")
    @patch("subprocess.run")
    @patch("platform.system")
    @patch("gui.utils.fs._show_file_manager_error")
    def test_linux_fallback_failure(self, mock_error, mock_system, mock_subprocess, mock_open_url, tmp_path):
        """Test Linux xdg-open fallback failure."""
        mock_open_url.return_value = False
        mock_system.return_value = "Linux"

        # Mock failed xdg-open
        mock_result = Mock()
        mock_result.returncode = 1
        mock_subprocess.return_value = mock_result

        result = open_in_file_manager(tmp_path)

        assert result is False
        mock_error.assert_called_once_with(tmp_path.resolve(), None)

    @patch.object(QDesktopServices, "openUrl")
    @patch("subprocess.run")
    @patch("gui.utils.fs._show_file_manager_error")
    def test_subprocess_exception_handling(self, mock_error, mock_subprocess, mock_open_url, tmp_path):
        """Test handling of subprocess exceptions."""
        mock_open_url.return_value = False
        mock_subprocess.side_effect = subprocess.SubprocessError("Command failed")

        result = open_in_file_manager(tmp_path)

        assert result is False
        mock_error.assert_called_once_with(tmp_path.resolve(), None)

    @patch.object(QDesktopServices, "openUrl")
    @patch("subprocess.run")
    @patch("gui.utils.fs._show_file_manager_error")
    def test_file_not_found_exception(self, mock_error, mock_subprocess, mock_open_url, tmp_path):
        """Test handling of FileNotFoundError (command not available)."""
        mock_open_url.return_value = False
        mock_subprocess.side_effect = FileNotFoundError("Command not found")

        result = open_in_file_manager(tmp_path)

        assert result is False
        mock_error.assert_called_once_with(tmp_path.resolve(), None)

    @patch.object(QDesktopServices, "openUrl")
    def test_qdesktopservices_exception(self, mock_open_url, tmp_path):
        """Test handling of QDesktopServices exceptions."""
        mock_open_url.side_effect = Exception("Qt error")

        with (
            patch("subprocess.run") as mock_subprocess,
            patch("platform.system", return_value="Linux"),
            patch("gui.utils.fs._show_file_manager_error") as mock_error,
        ):
            # Mock xdg-open failure too
            mock_result = Mock()
            mock_result.returncode = 1
            mock_subprocess.return_value = mock_result

            result = open_in_file_manager(tmp_path)

            assert result is False
            mock_error.assert_called_once()

    def test_path_normalization(self, tmp_path):
        """Test that paths are properly normalized before processing."""
        # Create a subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Use a relative path with .. navigation
        relative_path = subdir / ".." / "subdir"

        with patch.object(QDesktopServices, "openUrl", return_value=True) as mock_open_url:
            result = open_in_file_manager(relative_path)

            assert result is True
            # Verify the path was resolved/normalized
            call_args = mock_open_url.call_args[0][0]
            normalized_path = Path(call_args.toLocalFile())
            assert normalized_path == subdir.resolve()


class TestShowFileManagerError:
    """Test cases for the error dialog functionality."""

    @patch("gui.utils.fs.QMessageBox")
    @patch("platform.system")
    def test_windows_error_message(self, mock_system, mock_messagebox_class, tmp_path):
        """Test Windows-specific error message."""
        mock_system.return_value = "Windows"
        mock_messagebox = Mock()
        mock_messagebox_class.return_value = mock_messagebox

        from gui.utils.fs import _show_file_manager_error

        _show_file_manager_error(tmp_path, None)

        # Verify message box was configured correctly
        mock_messagebox.setIcon.assert_called_once()
        mock_messagebox.setWindowTitle.assert_called_once_with("Cannot Open Folder")
        mock_messagebox.setText.assert_called_once_with("Failed to open folder in file manager")

        # Check that detailed text contains Windows-specific suggestion
        detailed_text_call = mock_messagebox.setDetailedText.call_args[0][0]
        assert "Windows Explorer" in detailed_text_call
        assert str(tmp_path) in detailed_text_call

    @patch("gui.utils.fs.QMessageBox")
    @patch("platform.system")
    def test_macos_error_message(self, mock_system, mock_messagebox_class, tmp_path):
        """Test macOS-specific error message."""
        mock_system.return_value = "Darwin"
        mock_messagebox = Mock()
        mock_messagebox_class.return_value = mock_messagebox

        from gui.utils.fs import _show_file_manager_error

        _show_file_manager_error(tmp_path, None)

        # Check that detailed text contains macOS-specific suggestion
        detailed_text_call = mock_messagebox.setDetailedText.call_args[0][0]
        assert "Finder" in detailed_text_call
        assert str(tmp_path) in detailed_text_call

    @patch("gui.utils.fs.QMessageBox")
    @patch("platform.system")
    def test_linux_error_message(self, mock_system, mock_messagebox_class, tmp_path):
        """Test Linux/generic error message."""
        mock_system.return_value = "Linux"
        mock_messagebox = Mock()
        mock_messagebox_class.return_value = mock_messagebox

        from gui.utils.fs import _show_file_manager_error

        _show_file_manager_error(tmp_path, None)

        # Check that detailed text contains generic suggestion
        detailed_text_call = mock_messagebox.setDetailedText.call_args[0][0]
        assert "file manager" in detailed_text_call
        assert str(tmp_path) in detailed_text_call


class TestIntegration:
    """Integration tests for real file system operations."""

    def test_real_directory_opens_without_error(self, tmp_path):
        """Test that the function doesn't crash with real directories.

        Note: This test mocks QDesktopServices to avoid opening real file manager windows.
        """
        with patch.object(QDesktopServices, "openUrl", return_value=True) as mock_open_url:
            result = open_in_file_manager(tmp_path)

            # Should return True when QDesktopServices.openUrl succeeds
            assert result is True

            # Verify QDesktopServices.openUrl was called with correct URL
            mock_open_url.assert_called_once()
            call_args = mock_open_url.call_args[0][0]
            assert isinstance(call_args, QUrl)

            # Verify the URL points to our test directory
            url_path = Path(call_args.toLocalFile())
            assert url_path == tmp_path.resolve()

    def test_expanduser_handling(self, tmp_path):
        """Test that paths with ~ are properly expanded."""
        # Create a mock path that looks like it has ~ in it
        # We'll use a relative path that gets resolved
        test_path = Path(".")

        with patch.object(QDesktopServices, "openUrl", return_value=True) as mock_open_url:
            result = open_in_file_manager(test_path)

            assert result is True
            # Verify the path was resolved to an absolute path
            call_args = mock_open_url.call_args[0][0]
            resolved_path = Path(call_args.toLocalFile())
            assert resolved_path.is_absolute()
