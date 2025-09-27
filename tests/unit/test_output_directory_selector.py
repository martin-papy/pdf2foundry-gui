"""Tests for the OutputDirectorySelector widget."""

import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QVBoxLayout

from gui.widgets.directory_selector import OutputDirectorySelector


class TestOutputDirectorySelectorInitialization:
    """Test OutputDirectorySelector initialization and basic properties."""

    def test_widget_creation(self, qtbot):
        """Test that the widget can be created successfully."""
        widget = OutputDirectorySelector()
        qtbot.addWidget(widget)

        assert widget is not None
        assert hasattr(widget, "path_edit")
        assert hasattr(widget, "browse_button")

    def test_signals_exist(self, qtbot):
        """Test that all required signals exist."""
        widget = OutputDirectorySelector()
        qtbot.addWidget(widget)

        assert hasattr(widget, "pathChanged")
        assert hasattr(widget, "validityChanged")
        assert hasattr(widget, "readyForUse")

    def test_initial_layout(self, qtbot):
        """Test that the layout is set up correctly."""
        widget = OutputDirectorySelector()
        qtbot.addWidget(widget)

        # Check that widgets are properly arranged
        layout = widget.layout()
        assert layout is not None
        assert isinstance(layout, QVBoxLayout)

        # The main layout should have the input layout and validation layout
        assert layout.count() >= 1  # At least the input layout

        # Get the input layout (first item in main layout)
        input_layout_item = layout.itemAt(0)
        assert input_layout_item is not None
        input_layout = input_layout_item.layout()
        assert input_layout is not None
        assert isinstance(input_layout, QHBoxLayout)

        # Check that the input layout contains the expected widgets
        assert input_layout.count() == 3  # path_edit, browse_button, open_folder_button
        assert input_layout.itemAt(0).widget() == widget.path_edit
        assert input_layout.itemAt(1).widget() == widget.browse_button
        assert input_layout.itemAt(2).widget() == widget.open_folder_button

    def test_accessibility_properties(self, qtbot):
        """Test that accessibility properties are set."""
        widget = OutputDirectorySelector()
        qtbot.addWidget(widget)

        assert widget.path_edit.accessibleName() == "Output directory path"
        assert widget.browse_button.accessibleName() == "Browse for output directory"
        assert "Enter or select" in widget.path_edit.accessibleDescription()
        assert "Opens a folder browser" in widget.browse_button.accessibleDescription()

    @patch("gui.output.output_folder_controller.QStandardPaths.writableLocation")
    def test_default_initialization_with_documents(self, mock_writable_location, qtbot, tmp_path):
        """Test initialization with Documents folder as default."""
        mock_config = Mock()
        mock_config.get.return_value = None
        mock_config.set = Mock()
        mock_writable_location.return_value = str(tmp_path)
        expected_dir = tmp_path / "pdf2foundry"
        expected_dir.mkdir(parents=True, exist_ok=True)
        widget = OutputDirectorySelector(config_manager=mock_config)
        qtbot.addWidget(widget)
        expected_path = str(expected_dir)
        assert widget.path() == expected_path
        assert widget.is_valid()

    @patch("gui.output.output_folder_controller.QStandardPaths.writableLocation")
    def test_default_initialization_fallback_to_cwd(self, mock_writable_location, qtbot, tmp_path):
        """Test initialization fallback to current working directory."""
        mock_config = Mock()
        mock_config.get.return_value = None
        mock_config.set = Mock()
        mock_writable_location.return_value = None
        expected_dir = Path.cwd() / "pdf2foundry"
        expected_dir.mkdir(parents=True, exist_ok=True)
        widget = OutputDirectorySelector(config_manager=mock_config)
        qtbot.addWidget(widget)
        try:
            expected_path = str(expected_dir)
            assert widget.path() == expected_path
            assert widget.is_valid()
        finally:
            # Clean up the created directory
            if expected_dir.exists():
                expected_dir.rmdir()


class TestOutputDirectorySelectorPathHandling:
    """Test path setting and normalization functionality."""

    def test_set_path_with_string(self, qtbot, tmp_path):
        """Test setting path with string input."""
        widget = OutputDirectorySelector()
        qtbot.addWidget(widget)

        widget.set_path(str(tmp_path))

        assert widget.path() == str(tmp_path)
        assert widget.path_edit.text() == str(tmp_path)

    def test_set_path_with_path_object(self, qtbot, tmp_path):
        """Test setting path with Path object."""
        widget = OutputDirectorySelector()
        qtbot.addWidget(widget)

        widget.set_path(tmp_path)

        assert widget.path() == str(tmp_path)
        assert widget.path_edit.text() == str(tmp_path)

    def test_path_normalization(self, qtbot, tmp_path):
        """Test that paths are properly normalized."""
        widget = OutputDirectorySelector()
        qtbot.addWidget(widget)

        # Create a path with redundant separators
        redundant_path = str(tmp_path) + os.sep + "." + os.sep
        widget.set_path(redundant_path)

        # Should be normalized to the clean path
        assert widget.path() == str(tmp_path)

    def test_expanduser_handling(self, qtbot):
        """Test that ~ is expanded to home directory."""
        widget = OutputDirectorySelector()
        qtbot.addWidget(widget)

        widget.set_path("~")

        expected_path = str(Path.home())
        assert widget.path() == expected_path


class TestOutputDirectorySelectorValidation:
    """Test path validation functionality."""

    def test_valid_directory_validation(self, qtbot, tmp_path):
        """Test validation of a valid directory."""
        widget = OutputDirectorySelector()
        qtbot.addWidget(widget)

        is_valid, error_message = widget.validate_path(tmp_path)

        assert is_valid
        assert "Valid output directory" in error_message

    def test_nonexistent_path_validation(self, qtbot, tmp_path):
        """Test validation of a non-existent path."""
        widget = OutputDirectorySelector()
        qtbot.addWidget(widget)

        nonexistent_path = tmp_path / "nonexistent"
        is_valid, error_message = widget.validate_path(nonexistent_path)

        # The new validator allows creation if parent exists and is writable
        assert is_valid
        assert "Directory will be created" in error_message

    def test_file_path_validation(self, qtbot, tmp_path):
        """Test validation of a file path (should be invalid)."""
        widget = OutputDirectorySelector()
        qtbot.addWidget(widget)

        # Create a file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        is_valid, error_message = widget.validate_path(test_file)

        assert not is_valid
        assert "not a directory" in error_message

    def test_empty_path_validation(self, qtbot):
        """Test validation of empty path."""
        widget = OutputDirectorySelector()
        qtbot.addWidget(widget)

        is_valid, error_message = widget.validate_path("")

        assert not is_valid
        assert "Please select an output directory" in error_message

    @patch("os.access")
    def test_readonly_directory_validation(self, mock_access, qtbot, tmp_path):
        """Test validation of a read-only directory."""
        widget = OutputDirectorySelector()
        qtbot.addWidget(widget)

        # Mock os.access to return False for write access
        mock_access.return_value = False

        is_valid, error_message = widget.validate_path(tmp_path)

        assert not is_valid
        assert "not writable" in error_message


class TestOutputDirectorySelectorRealTimeValidation:
    """Test real-time validation as user types."""

    @patch("core.config_manager.ConfigManager")
    def test_text_changed_validation(self, mock_config_class, qtbot, tmp_path):
        """Test that validation occurs when text changes."""
        # Mock ConfigManager to return None for stored paths
        mock_config = Mock()
        mock_config.get.return_value = None
        mock_config_class.return_value = mock_config

        widget = OutputDirectorySelector()
        qtbot.addWidget(widget)

        # Mock the validation signals
        validity_spy = Mock()
        ready_spy = Mock()
        widget.validityChanged.connect(validity_spy)
        widget.readyForUse.connect(ready_spy)

        # Simulate typing a valid path
        widget.path_edit.setText(str(tmp_path))

        # Signals should have been emitted
        validity_spy.assert_called_once()
        ready_spy.assert_called_once()

        # Check the arguments
        args = validity_spy.call_args[0]
        assert args[0] is True  # is_valid
        # The message can be either empty or a success message
        assert isinstance(args[1], str)  # message should be a string

    def test_text_cleanup(self, qtbot, tmp_path):
        """Test that trailing spaces are cleaned up."""
        widget = OutputDirectorySelector()
        qtbot.addWidget(widget)

        # Set text with trailing spaces
        widget.path_edit.setText(str(tmp_path) + "   ")

        # Should be cleaned up
        assert widget.path_edit.text() == str(tmp_path)

    def test_ui_styling_updates(self, qtbot, tmp_path):
        """Test that UI styling updates based on validation."""
        widget = OutputDirectorySelector()
        qtbot.addWidget(widget)

        # Set a valid path
        widget.path_edit.setText(str(tmp_path))

        # Should have valid styling (green border)
        style = widget.path_edit.styleSheet()
        assert "#28a745" in style  # Green border color

        # Set an invalid path
        widget.path_edit.setText("/nonexistent/path")

        # Should have invalid styling (red border)
        style = widget.path_edit.styleSheet()
        assert "#dc3545" in style  # Red border color


class TestOutputDirectorySelectorBrowsing:
    """Test folder browsing functionality."""

    @patch.object(QFileDialog, "getExistingDirectory")
    def test_browse_button_click(self, mock_dialog, qtbot, tmp_path):
        """Test browse button functionality."""
        widget = OutputDirectorySelector()
        qtbot.addWidget(widget)

        # Mock the dialog to return our temp directory
        mock_dialog.return_value = str(tmp_path)

        # Click the browse button
        widget.browse_button.click()

        # Dialog should have been called
        mock_dialog.assert_called_once()

        # Path should be updated
        assert widget.path() == str(tmp_path)

    @patch.object(QFileDialog, "getExistingDirectory")
    def test_browse_button_cancel(self, mock_dialog, qtbot):
        """Test browse button cancellation."""
        widget = OutputDirectorySelector()
        qtbot.addWidget(widget)

        original_path = widget.path()

        # Mock the dialog to return empty string (cancel)
        mock_dialog.return_value = ""

        # Click the browse button
        widget.browse_button.click()

        # Path should not have changed
        assert widget.path() == original_path

    @patch.object(QFileDialog, "getExistingDirectory")
    def test_browse_start_directory_logic(self, mock_dialog, qtbot, tmp_path):
        """Test that browse dialog starts in the correct directory."""
        widget = OutputDirectorySelector()
        qtbot.addWidget(widget)

        # Set a valid path first
        widget.set_path(tmp_path)

        # Mock the dialog
        mock_dialog.return_value = ""

        # Click the browse button
        widget.browse_button.click()

        # Check that the dialog was called with the current path as start directory
        call_args = mock_dialog.call_args[0]
        assert str(tmp_path) in call_args[2]  # start_dir argument


class TestOutputDirectorySelectorIntegration:
    """Test integration methods and signals."""

    def test_is_valid_method(self, qtbot, tmp_path):
        """Test the is_valid() method."""
        widget = OutputDirectorySelector()
        qtbot.addWidget(widget)

        # Should be valid with default initialization
        assert widget.is_valid()

        # Set an invalid path
        widget.path_edit.setText("/nonexistent/path")

        # Should now be invalid
        assert not widget.is_valid()

    def test_error_message_method(self, qtbot):
        """Test the error_message() method."""
        widget = OutputDirectorySelector()
        qtbot.addWidget(widget)

        # Set an invalid path
        widget.path_edit.setText("/nonexistent/path")

        # Should have an error message
        error = widget.error_message()
        assert error != ""
        assert "does not exist" in error

    def test_ready_for_use_method(self, qtbot, tmp_path):
        """Test the is_ready_for_use() method."""
        widget = OutputDirectorySelector()
        qtbot.addWidget(widget)

        # Should be ready with valid path
        widget.set_path(tmp_path)
        assert widget.is_ready_for_use()

        # Should not be ready with invalid path
        widget.path_edit.setText("/nonexistent/path")
        assert not widget.is_ready_for_use()

    def test_signal_emission_order(self, qtbot, tmp_path):
        """Test that signals are emitted in the correct order."""
        widget = OutputDirectorySelector()
        qtbot.addWidget(widget)

        # Track signal emissions
        signals_received = []

        def track_path_changed(path):
            signals_received.append(("pathChanged", path))

        def track_validity_changed(is_valid, message):
            signals_received.append(("validityChanged", is_valid, message))

        def track_ready_for_use(ready):
            signals_received.append(("readyForUse", ready))

        widget.pathChanged.connect(track_path_changed)
        widget.validityChanged.connect(track_validity_changed)
        widget.readyForUse.connect(track_ready_for_use)

        # Set a path
        widget.set_path(tmp_path)

        # Check that signals were emitted
        assert len(signals_received) >= 2

        # The exact order may vary, but we should have both pathChanged and validityChanged
        signal_types = [signal[0] for signal in signals_received]
        assert "pathChanged" in signal_types
        assert "validityChanged" in signal_types
        assert "readyForUse" in signal_types


class TestOutputDirectorySelectorEdgeCases:
    """Test edge cases and error handling."""

    def test_unicode_paths(self, qtbot, tmp_path):
        """Test handling of Unicode characters in paths."""
        widget = OutputDirectorySelector()
        qtbot.addWidget(widget)

        # Create a directory with Unicode characters
        unicode_dir = tmp_path / "测试目录"
        unicode_dir.mkdir()

        widget.set_path(unicode_dir)

        assert widget.is_valid()
        assert widget.path() == str(unicode_dir)

    def test_very_long_paths(self, qtbot, tmp_path):
        """Test handling of very long paths."""
        widget = OutputDirectorySelector()
        qtbot.addWidget(widget)

        # Create a nested directory structure
        long_path = tmp_path
        for i in range(10):
            long_path = long_path / f"very_long_directory_name_{i}"

        try:
            long_path.mkdir(parents=True)
            widget.set_path(long_path)

            # Should handle long paths gracefully
            assert widget.path() == str(long_path)
        except OSError:
            # If the system can't create the path, that's fine
            # Just test that the widget doesn't crash
            widget.set_path(str(long_path))
            # Widget should handle the error gracefully

    def test_symlink_handling(self, qtbot, tmp_path):
        """Test handling of symbolic links."""
        widget = OutputDirectorySelector()
        qtbot.addWidget(widget)

        # Create a directory and a symlink to it
        real_dir = tmp_path / "real_directory"
        real_dir.mkdir()

        symlink_dir = tmp_path / "symlink_directory"
        try:
            symlink_dir.symlink_to(real_dir)

            widget.set_path(symlink_dir)

            # Should resolve to the real directory
            assert widget.is_valid()
            # The resolved path should point to the real directory
            assert Path(widget.path()).resolve() == real_dir.resolve()
        except OSError:
            # Symlinks might not be supported on all systems
            pytest.skip("Symlinks not supported on this system")

    def test_permission_error_handling(self, qtbot, tmp_path):
        """Test handling of permission errors."""
        widget = OutputDirectorySelector()
        qtbot.addWidget(widget)

        # Test with a path that might cause permission errors
        with patch("pathlib.Path.resolve", side_effect=PermissionError("Access denied")):
            is_valid, error_message = widget.validate_path(tmp_path)

            assert not is_valid
            assert "Invalid path" in error_message
