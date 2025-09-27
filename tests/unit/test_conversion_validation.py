"""
Tests for the ConversionValidator class.

This module tests validation utilities for conversion operations including
output directory validation, disk space checks, and preflight checks.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from PySide6.QtWidgets import QApplication

from gui.conversion.validation import ConversionValidator


class TestConversionValidator:
    """Test cases for ConversionValidator."""

    def setup_method(self):
        """Set up test fixtures."""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()

        # Create a mock main window
        self.mock_main_window = Mock()
        self.mock_main_window.ui = Mock()
        self.mock_main_window.file_handler = Mock()
        self.mock_main_window.conversion_handler = Mock()

        # Create validator instance
        self.validator = ConversionValidator(self.mock_main_window)

    def teardown_method(self):
        """Clean up after tests."""
        if hasattr(self, "app") and self.app:
            self.app.quit()


class TestOutputDirectoryValidation(TestConversionValidator):
    """Test output directory validation."""

    def test_empty_output_path(self):
        """Test validation fails for empty output path."""
        is_valid, error = self.validator._validate_output_directory("")
        assert not is_valid
        assert "cannot be empty" in error

    def test_whitespace_only_path(self):
        """Test validation fails for whitespace-only path."""
        is_valid, error = self.validator._validate_output_directory("   ")
        assert not is_valid
        assert "cannot be empty" in error

    def test_invalid_path_format(self):
        """Test validation fails for invalid path format."""
        with patch("pathlib.Path.resolve", side_effect=OSError("Invalid path")):
            is_valid, error = self.validator._validate_output_directory("/invalid/path")
            assert not is_valid
            assert "Invalid path format" in error

    def test_reserved_windows_names(self):
        """Test validation fails for Windows reserved names."""
        reserved_names = ["CON", "PRN", "AUX", "NUL", "COM1", "LPT1"]

        for name in reserved_names:
            with patch("pathlib.Path.resolve") as mock_resolve:
                mock_path = Mock()
                mock_path.name = name
                mock_resolve.return_value = mock_path

                is_valid, error = self.validator._validate_output_directory(f"/path/{name}")
                assert not is_valid
                assert "reserved name" in error

    def test_path_too_long(self):
        """Test validation fails for paths that are too long."""
        # Create a path that's actually too long
        long_path = "/" + "a" * 300

        is_valid, error = self.validator._validate_output_directory(long_path)
        assert not is_valid
        assert "too long" in error

    def test_existing_file_not_directory(self):
        """Test validation fails when path exists but is not a directory."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            try:
                is_valid, error = self.validator._validate_output_directory(temp_file.name)
                assert not is_valid
                assert "not a directory" in error
            finally:
                os.unlink(temp_file.name)

    def test_existing_directory_no_write_permission(self):
        """Test validation fails for existing directory without write permission."""
        with tempfile.TemporaryDirectory() as temp_dir, patch("os.access", return_value=False):
            is_valid, error = self.validator._validate_output_directory(temp_dir)
            assert not is_valid
            assert "No write permission" in error

    def test_existing_writable_directory(self):
        """Test validation succeeds for existing writable directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            is_valid, error = self.validator._validate_output_directory(temp_dir)
            assert is_valid
            assert error == ""

    def test_nonexistent_directory_creation_success(self):
        """Test validation succeeds when directory can be created."""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = Path(temp_dir) / "new_directory"
            is_valid, error = self.validator._validate_output_directory(str(new_dir))
            assert is_valid
            assert error == ""
            assert new_dir.exists()

    def test_nonexistent_directory_parent_no_permission(self):
        """Test validation fails when parent directory has no write permission."""
        # Use a non-existent parent path to trigger the parent creation logic
        nonexistent_parent = "/nonexistent/parent/directory"
        new_dir = Path(nonexistent_parent) / "new_directory"

        with patch("pathlib.Path.resolve") as mock_resolve:
            mock_path = Mock()
            mock_path.exists.return_value = False
            mock_parent = Mock()
            mock_parent.exists.return_value = True  # Parent exists but no write permission
            mock_path.parent = mock_parent
            mock_resolve.return_value = mock_path

            with patch("os.access", return_value=False):  # No write permission
                is_valid, error = self.validator._validate_output_directory(str(new_dir))
                assert not is_valid
                assert "No write permission for parent directory" in error

    def test_directory_creation_fails(self):
        """Test validation fails when directory creation fails."""
        with patch("pathlib.Path.resolve") as mock_resolve:
            mock_path = Mock()
            mock_path.name = "test"
            mock_path.exists.return_value = False
            mock_path.parent.exists.return_value = True
            mock_path.mkdir.side_effect = PermissionError("Permission denied")
            mock_resolve.return_value = mock_path

            with patch("os.access", return_value=True):
                is_valid, error = self.validator._validate_output_directory("/test/path")
                assert not is_valid
                assert "Cannot create directory" in error

    def test_file_write_test_fails(self):
        """Test validation fails when file write test fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = Path(temp_dir) / "new_directory"

            with patch.object(Path, "write_text", side_effect=PermissionError("Write failed")):
                is_valid, error = self.validator._validate_output_directory(str(new_dir))
                assert not is_valid
                assert "Cannot write to directory" in error


class TestDiskSpaceCheck(TestConversionValidator):
    """Test disk space checking functionality."""

    def test_invalid_path_format(self):
        """Test disk space check fails for invalid path format."""
        with patch("pathlib.Path.resolve", side_effect=ValueError("Invalid path")):
            has_space, error = self.validator._check_disk_space("/invalid/path")
            assert not has_space
            assert "Failed to check disk space" in error

    def test_no_accessible_parent_directory(self):
        """Test disk space check fails when no accessible parent directory exists."""
        with patch("pathlib.Path.resolve") as mock_resolve:
            mock_path = Mock()
            mock_path.exists.return_value = False
            mock_path.parent = mock_path  # Simulate root directory
            mock_resolve.return_value = mock_path

            has_space, error = self.validator._check_disk_space("/nonexistent/path")
            assert not has_space
            assert "no accessible parent directory" in error

    def test_insufficient_disk_space(self):
        """Test disk space check fails when insufficient space available."""
        # 50 MB free
        disk_usage_return = (1000, 900, 50 * 1024 * 1024)
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch("shutil.disk_usage", return_value=disk_usage_return),
        ):
            has_space, error = self.validator._check_disk_space(temp_dir, estimated_size_mb=100)
            assert not has_space
            assert "Insufficient disk space" in error

    def test_sufficient_disk_space(self):
        """Test disk space check succeeds when sufficient space available."""
        # 500 MB free
        disk_usage_return = (1000, 500, 500 * 1024 * 1024)
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch("shutil.disk_usage", return_value=disk_usage_return),
        ):
            has_space, error = self.validator._check_disk_space(temp_dir, estimated_size_mb=100)
            assert has_space
            assert error == ""

    def test_disk_usage_os_error(self):
        """Test disk space check handles OS errors gracefully."""
        with patch("shutil.disk_usage", side_effect=OSError("Disk error")):
            has_space, error = self.validator._check_disk_space("/some/path")
            assert not has_space
            assert "Failed to check disk space" in error

    def test_nonexistent_path_finds_parent(self):
        """Test disk space check finds existing parent for nonexistent path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_path = Path(temp_dir) / "nonexistent" / "subdirectory"

            # Mock shutil.disk_usage to return sufficient space
            with patch("shutil.disk_usage", return_value=(1000, 500, 500 * 1024 * 1024)):
                has_space, error = self.validator._check_disk_space(str(nonexistent_path))
                assert has_space
                assert error == ""


class TestPreflightChecks(TestConversionValidator):
    """Test preflight validation checks."""

    def test_conversion_already_in_progress(self):
        """Test preflight check fails when conversion is already in progress."""
        self.mock_main_window.conversion_handler._in_progress = True

        all_passed, error = self.validator._perform_preflight_checks()
        assert not all_passed
        assert "already in progress" in error

    def test_conversion_was_cancelled(self):
        """Test preflight check fails when conversion was cancelled."""
        self.mock_main_window.conversion_handler._in_progress = False
        self.mock_main_window.conversion_handler._cancel_requested = True

        all_passed, error = self.validator._perform_preflight_checks()
        assert not all_passed
        assert "was cancelled" in error

    def test_no_output_directory_selector(self):
        """Test preflight check fails when output directory selector not available."""
        self.mock_main_window.conversion_handler._in_progress = False
        self.mock_main_window.conversion_handler._cancel_requested = False
        self.mock_main_window.ui.output_dir_selector = None

        all_passed, error = self.validator._perform_preflight_checks()
        assert not all_passed
        assert "Output directory selector not available" in error

    def test_no_output_directory_selected(self):
        """Test preflight check fails when no output directory is selected."""
        self.mock_main_window.conversion_handler._in_progress = False
        self.mock_main_window.conversion_handler._cancel_requested = False
        self.mock_main_window.ui.output_dir_selector = Mock()
        self.mock_main_window.ui.output_dir_selector.path.return_value = ""

        all_passed, error = self.validator._perform_preflight_checks()
        assert not all_passed
        assert "No output directory selected" in error

    def test_output_directory_validation_fails(self):
        """Test preflight check fails when output directory validation fails."""
        self.mock_main_window.conversion_handler._in_progress = False
        self.mock_main_window.conversion_handler._cancel_requested = False
        self.mock_main_window.ui.output_dir_selector = Mock()
        self.mock_main_window.ui.output_dir_selector.path.return_value = "/invalid/path"

        with patch.object(self.validator, "_validate_output_directory", return_value=(False, "Invalid directory")):
            all_passed, error = self.validator._perform_preflight_checks()
            assert not all_passed
            assert "Output directory validation failed" in error

    def test_disk_space_check_fails(self):
        """Test preflight check fails when disk space check fails."""
        self.mock_main_window.conversion_handler._in_progress = False
        self.mock_main_window.conversion_handler._cancel_requested = False
        self.mock_main_window.ui.output_dir_selector = Mock()
        self.mock_main_window.ui.output_dir_selector.path.return_value = "/valid/path"

        with (
            patch.object(self.validator, "_validate_output_directory", return_value=(True, "")),
            patch.object(self.validator, "_check_disk_space", return_value=(False, "Insufficient space")),
        ):
            all_passed, error = self.validator._perform_preflight_checks()
            assert not all_passed
            assert "Disk space check failed" in error

    def test_no_pdf_file_selected(self):
        """Test preflight check fails when no PDF file is selected."""
        self.mock_main_window.conversion_handler._in_progress = False
        self.mock_main_window.conversion_handler._cancel_requested = False
        self.mock_main_window.ui.output_dir_selector = Mock()
        self.mock_main_window.ui.output_dir_selector.path.return_value = "/valid/path"
        self.mock_main_window.file_handler.get_selected_pdf_path.return_value = None

        with (
            patch.object(self.validator, "_validate_output_directory", return_value=(True, "")),
            patch.object(self.validator, "_check_disk_space", return_value=(True, "")),
        ):
            all_passed, error = self.validator._perform_preflight_checks()
            assert not all_passed
            assert "No PDF file selected" in error

    def test_pdf_file_does_not_exist(self):
        """Test preflight check fails when selected PDF file does not exist."""
        self.mock_main_window.conversion_handler._in_progress = False
        self.mock_main_window.conversion_handler._cancel_requested = False
        self.mock_main_window.ui.output_dir_selector = Mock()
        self.mock_main_window.ui.output_dir_selector.path.return_value = "/valid/path"
        self.mock_main_window.file_handler.get_selected_pdf_path.return_value = "/nonexistent/file.pdf"

        with (
            patch.object(self.validator, "_validate_output_directory", return_value=(True, "")),
            patch.object(self.validator, "_check_disk_space", return_value=(True, "")),
        ):
            all_passed, error = self.validator._perform_preflight_checks()
            assert not all_passed
            assert "does not exist" in error

    def test_pdf_file_not_readable(self):
        """Test preflight check fails when PDF file is not readable."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            try:
                self.mock_main_window.conversion_handler._in_progress = False
                self.mock_main_window.conversion_handler._cancel_requested = False
                self.mock_main_window.ui.output_dir_selector = Mock()
                self.mock_main_window.ui.output_dir_selector.path.return_value = "/valid/path"
                self.mock_main_window.file_handler.get_selected_pdf_path.return_value = temp_file.name

                with (
                    patch.object(self.validator, "_validate_output_directory", return_value=(True, "")),
                    patch.object(self.validator, "_check_disk_space", return_value=(True, "")),
                    patch("os.access", return_value=False),
                ):
                    all_passed, error = self.validator._perform_preflight_checks()
                    assert not all_passed
                    assert "Cannot read selected PDF file" in error
            finally:
                os.unlink(temp_file.name)

    def test_no_module_id_input(self):
        """Test preflight check fails when module ID input is not available."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            try:
                self.mock_main_window.conversion_handler._in_progress = False
                self.mock_main_window.conversion_handler._cancel_requested = False
                self.mock_main_window.ui.output_dir_selector = Mock()
                self.mock_main_window.ui.output_dir_selector.path.return_value = "/valid/path"
                self.mock_main_window.file_handler.get_selected_pdf_path.return_value = temp_file.name
                self.mock_main_window.ui.module_id_input = None

                with (
                    patch.object(self.validator, "_validate_output_directory", return_value=(True, "")),
                    patch.object(self.validator, "_check_disk_space", return_value=(True, "")),
                    patch("os.access", return_value=True),
                ):
                    all_passed, error = self.validator._perform_preflight_checks()
                    assert not all_passed
                    assert "Module ID is required" in error
            finally:
                os.unlink(temp_file.name)

    def test_empty_module_id(self):
        """Test preflight check fails when module ID is empty."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            try:
                self.mock_main_window.conversion_handler._in_progress = False
                self.mock_main_window.conversion_handler._cancel_requested = False
                self.mock_main_window.ui.output_dir_selector = Mock()
                self.mock_main_window.ui.output_dir_selector.path.return_value = "/valid/path"
                self.mock_main_window.file_handler.get_selected_pdf_path.return_value = temp_file.name
                self.mock_main_window.ui.module_id_input = Mock()
                self.mock_main_window.ui.module_id_input.text.return_value = "   "

                with (
                    patch.object(self.validator, "_validate_output_directory", return_value=(True, "")),
                    patch.object(self.validator, "_check_disk_space", return_value=(True, "")),
                    patch("os.access", return_value=True),
                ):
                    all_passed, error = self.validator._perform_preflight_checks()
                    assert not all_passed
                    assert "Module ID is required" in error
            finally:
                os.unlink(temp_file.name)

    def test_no_module_title_input(self):
        """Test preflight check fails when module title input is not available."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            try:
                self.mock_main_window.conversion_handler._in_progress = False
                self.mock_main_window.conversion_handler._cancel_requested = False
                self.mock_main_window.ui.output_dir_selector = Mock()
                self.mock_main_window.ui.output_dir_selector.path.return_value = "/valid/path"
                self.mock_main_window.file_handler.get_selected_pdf_path.return_value = temp_file.name
                self.mock_main_window.ui.module_id_input = Mock()
                self.mock_main_window.ui.module_id_input.text.return_value = "valid-module-id"
                self.mock_main_window.ui.module_title_input = None

                with (
                    patch.object(self.validator, "_validate_output_directory", return_value=(True, "")),
                    patch.object(self.validator, "_check_disk_space", return_value=(True, "")),
                    patch("os.access", return_value=True),
                ):
                    all_passed, error = self.validator._perform_preflight_checks()
                    assert not all_passed
                    assert "Module title is required" in error
            finally:
                os.unlink(temp_file.name)

    def test_empty_module_title(self):
        """Test preflight check fails when module title is empty."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            try:
                self.mock_main_window.conversion_handler._in_progress = False
                self.mock_main_window.conversion_handler._cancel_requested = False
                self.mock_main_window.ui.output_dir_selector = Mock()
                self.mock_main_window.ui.output_dir_selector.path.return_value = "/valid/path"
                self.mock_main_window.file_handler.get_selected_pdf_path.return_value = temp_file.name
                self.mock_main_window.ui.module_id_input = Mock()
                self.mock_main_window.ui.module_id_input.text.return_value = "valid-module-id"
                self.mock_main_window.ui.module_title_input = Mock()
                self.mock_main_window.ui.module_title_input.text.return_value = "   "

                with (
                    patch.object(self.validator, "_validate_output_directory", return_value=(True, "")),
                    patch.object(self.validator, "_check_disk_space", return_value=(True, "")),
                    patch("os.access", return_value=True),
                ):
                    all_passed, error = self.validator._perform_preflight_checks()
                    assert not all_passed
                    assert "Module title is required" in error
            finally:
                os.unlink(temp_file.name)

    def test_all_preflight_checks_pass(self):
        """Test preflight check succeeds when all validations pass."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            try:
                self.mock_main_window.conversion_handler._in_progress = False
                self.mock_main_window.conversion_handler._cancel_requested = False
                self.mock_main_window.ui.output_dir_selector = Mock()
                self.mock_main_window.ui.output_dir_selector.path.return_value = "/valid/path"
                self.mock_main_window.file_handler.get_selected_pdf_path.return_value = temp_file.name
                self.mock_main_window.ui.module_id_input = Mock()
                self.mock_main_window.ui.module_id_input.text.return_value = "valid-module-id"
                self.mock_main_window.ui.module_title_input = Mock()
                self.mock_main_window.ui.module_title_input.text.return_value = "Valid Module Title"

                with (
                    patch.object(self.validator, "_validate_output_directory", return_value=(True, "")),
                    patch.object(self.validator, "_check_disk_space", return_value=(True, "")),
                    patch("os.access", return_value=True),
                ):
                    all_passed, error = self.validator._perform_preflight_checks()
                    assert all_passed
                    assert error == ""
            finally:
                os.unlink(temp_file.name)

    def test_missing_conversion_handler_attribute(self):
        """Test preflight check handles missing conversion_handler attribute gracefully."""
        # Remove the conversion_handler attribute
        delattr(self.mock_main_window, "conversion_handler")

        self.mock_main_window.ui.output_dir_selector = Mock()
        self.mock_main_window.ui.output_dir_selector.path.return_value = "/valid/path"
        self.mock_main_window.file_handler.get_selected_pdf_path.return_value = None

        with (
            patch.object(self.validator, "_validate_output_directory", return_value=(True, "")),
            patch.object(self.validator, "_check_disk_space", return_value=(True, "")),
        ):
            # Should not raise an exception and should continue with other checks
            all_passed, error = self.validator._perform_preflight_checks()
            # Will fail on PDF validation, but shouldn't crash on conversion handler check
            assert not all_passed
            assert "No PDF file selected" in error
