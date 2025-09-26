"""
Tests for GUI mapping functionality.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from core.conversion_config import OcrMode, PictureDescriptionMode, TableMode
from core.gui_mapping import (
    GuiConfigMapper,
    GuiMappingError,
    build_config_from_gui,
    extract_full_gui_state,
)


class TestGuiConfigMapper:
    """Test GuiConfigMapper functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mapper = GuiConfigMapper()
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_pdf = self.temp_dir / "test.pdf"
        self.test_pdf.write_text("fake pdf content")
        self.output_dir = self.temp_dir / "output"
        self.output_dir.mkdir()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_build_config_from_gui_basic(self):
        """Test building config from basic GUI state."""
        gui_state = {
            "pdf_path": str(self.test_pdf),
            "mod_id": "test-module",
            "mod_title": "Test Module",
            "author": "Test Author",
            "output_dir": str(self.output_dir),
        }

        config = self.mapper.build_config_from_gui(gui_state)

        assert config.pdf.resolve() == self.test_pdf.resolve()
        assert config.mod_id == "test-module"
        assert config.mod_title == "Test Module"
        assert config.author == "Test Author"
        assert config.out_dir.resolve() == self.output_dir.resolve()

    def test_build_config_from_gui_all_fields(self):
        """Test building config with all possible GUI fields."""
        gui_state = {
            "pdf_path": str(self.test_pdf),
            "mod_id": "test-module",
            "mod_title": "Test Module",
            "author": "Test Author",
            "license": "MIT",
            "pack_name": "custom-pack",
            "output_dir": str(self.output_dir),
            "deterministic_ids": True,
            "toc": False,
            "tables": "structured",
            "ocr": "on",
            "picture_descriptions": True,
            "vlm_repo_id": "microsoft/Florence-2-base",
            "pages": "1,3,5-10",
            "workers": 4,
            "reflow_columns": True,
            "compile_pack": True,
            "verbose": 2,
        }

        config = self.mapper.build_config_from_gui(gui_state)

        assert config.pdf.resolve() == self.test_pdf.resolve()
        assert config.mod_id == "test-module"
        assert config.mod_title == "Test Module"
        assert config.author == "Test Author"
        assert config.license == "MIT"
        assert config.pack_name == "custom-pack"
        assert config.out_dir.resolve() == self.output_dir.resolve()
        assert config.deterministic_ids is True
        assert config.toc is False
        assert config.tables == TableMode.STRUCTURED
        assert config.ocr == OcrMode.ON
        assert config.picture_descriptions == PictureDescriptionMode.ON
        assert config.vlm_repo_id == "microsoft/Florence-2-base"
        assert config.pages == [1, 3, 5, 6, 7, 8, 9, 10]
        assert config.workers == 4
        assert config.reflow_columns is True
        assert config.compile_pack is True
        assert config.verbose == 2

    def test_build_config_from_gui_missing_required(self):
        """Test building config with missing required fields."""
        gui_state = {
            "author": "Test Author",
        }

        with pytest.raises(GuiMappingError) as exc_info:
            self.mapper.build_config_from_gui(gui_state)

        assert "Validation failed" in str(exc_info.value)
        assert exc_info.value.field is not None

    def test_convert_gui_value_paths(self):
        """Test converting path values."""
        # String path
        result = self.mapper._convert_gui_value("pdf_path", "/test/file.pdf", "pdf")
        assert result == Path("/test/file.pdf")

        # Path object
        result = self.mapper._convert_gui_value("pdf_path", Path("/test/file.pdf"), "pdf")
        assert result == Path("/test/file.pdf")

        # Empty string
        result = self.mapper._convert_gui_value("pdf_path", "", "pdf")
        assert result is None

        # None
        result = self.mapper._convert_gui_value("pdf_path", None, "pdf")
        assert result is None

    def test_convert_gui_value_strings(self):
        """Test converting string values."""
        result = self.mapper._convert_gui_value("mod_id", "test-module", "mod_id")
        assert result == "test-module"

        # With whitespace
        result = self.mapper._convert_gui_value("mod_id", "  test-module  ", "mod_id")
        assert result == "test-module"

        # Empty string
        result = self.mapper._convert_gui_value("mod_id", "", "mod_id")
        assert result == ""

        # None
        result = self.mapper._convert_gui_value("mod_id", None, "mod_id")
        assert result == ""

    def test_convert_gui_value_booleans(self):
        """Test converting boolean values."""
        # Boolean
        result = self.mapper._convert_gui_value("toc", True, "toc")
        assert result is True

        # String representations
        result = self.mapper._convert_gui_value("toc", "true", "toc")
        assert result is True

        result = self.mapper._convert_gui_value("toc", "false", "toc")
        assert result is False

        result = self.mapper._convert_gui_value("toc", "1", "toc")
        assert result is True

        result = self.mapper._convert_gui_value("toc", "0", "toc")
        assert result is False

    def test_convert_gui_value_enums(self):
        """Test converting enum values."""
        # Tables enum
        result = self.mapper._convert_gui_value("tables", "structured", "tables")
        assert result == TableMode.STRUCTURED

        # OCR enum
        result = self.mapper._convert_gui_value("ocr", "on", "ocr")
        assert result == OcrMode.ON

        # Picture descriptions from boolean
        result = self.mapper._convert_gui_value("picture_descriptions", True, "picture_descriptions")
        assert result == PictureDescriptionMode.ON

        result = self.mapper._convert_gui_value("picture_descriptions", False, "picture_descriptions")
        assert result == PictureDescriptionMode.OFF

        # Picture descriptions from string
        result = self.mapper._convert_gui_value("picture_descriptions", "on", "picture_descriptions")
        assert result == PictureDescriptionMode.ON

    def test_convert_gui_value_numeric(self):
        """Test converting numeric values."""
        # Integer
        result = self.mapper._convert_gui_value("workers", 4, "workers")
        assert result == 4

        # String number
        result = self.mapper._convert_gui_value("workers", "4", "workers")
        assert result == 4

        # Empty string (default to 1)
        result = self.mapper._convert_gui_value("workers", "", "workers")
        assert result == 1

        # Float
        result = self.mapper._convert_gui_value("workers", 4.7, "workers")
        assert result == 4

    def test_convert_gui_value_pages(self):
        """Test converting page range values."""
        # String range
        result = self.mapper._convert_gui_value("pages", "1,3,5-7", "pages")
        assert result == [1, 3, 5, 6, 7]

        # List of pages
        result = self.mapper._convert_gui_value("pages", [1, 3, 5], "pages")
        assert result == [1, 3, 5]

        # Empty string
        result = self.mapper._convert_gui_value("pages", "", "pages")
        assert result is None

        # None
        result = self.mapper._convert_gui_value("pages", None, "pages")
        assert result is None

    def test_convert_gui_value_invalid_enum(self):
        """Test converting invalid enum values."""
        with pytest.raises(GuiMappingError):
            self.mapper._convert_gui_value("tables", "invalid-mode", "tables")

    def test_convert_gui_value_invalid_pages(self):
        """Test converting invalid page ranges."""
        with pytest.raises(GuiMappingError):
            self.mapper._convert_gui_value("pages", "invalid-range", "pages")

    def test_map_config_field_to_gui(self):
        """Test mapping config fields back to GUI fields."""
        assert self.mapper._map_config_field_to_gui("pdf") == "pdf_path"
        assert self.mapper._map_config_field_to_gui("mod_id") == "mod_id"
        assert self.mapper._map_config_field_to_gui("out_dir") == "output_dir"
        assert self.mapper._map_config_field_to_gui("nonexistent") is None

    def test_extract_gui_state_from_settings_dialog(self):
        """Test extracting GUI state from settings dialog."""
        # Create mock dialog
        dialog = Mock()
        dialog.author_edit.text.return_value = "Test Author"
        dialog.license_edit.text.return_value = "MIT"
        dialog.pack_name_edit.text.return_value = "custom-pack"
        dialog.output_dir_selector.path.return_value = "/test/output"
        dialog.deterministic_ids_checkbox.isChecked.return_value = True
        dialog.toc_checkbox.isChecked.return_value = False
        dialog.tables_combo.currentText.return_value = "structured"
        dialog.ocr_combo.currentText.return_value = "on"
        dialog.picture_descriptions_checkbox.isChecked.return_value = True
        dialog.vlm_repo_edit.text.return_value = "microsoft/Florence-2-base"
        dialog.pages_edit.text.return_value = "1,3,5-7"

        gui_state = self.mapper.extract_gui_state_from_settings_dialog(dialog)

        assert gui_state["author"] == "Test Author"
        assert gui_state["license"] == "MIT"
        assert gui_state["pack_name"] == "custom-pack"
        assert gui_state["output_dir"] == "/test/output"
        assert gui_state["deterministic_ids"] is True
        assert gui_state["toc"] is False
        assert gui_state["tables"] == "structured"
        assert gui_state["ocr"] == "on"
        assert gui_state["picture_descriptions"] is True
        assert gui_state["vlm_repo_id"] == "microsoft/Florence-2-base"
        assert gui_state["pages"] == "1,3,5-7"

    def test_extract_gui_state_from_settings_dialog_missing_widgets(self):
        """Test extracting from dialog with missing widgets."""
        # Create mock dialog with only some widgets
        dialog = Mock()
        dialog.author_edit.text.return_value = "Test Author"
        # Remove other attributes
        delattr(dialog, "license_edit")

        gui_state = self.mapper.extract_gui_state_from_settings_dialog(dialog)

        assert gui_state["author"] == "Test Author"
        assert "license" not in gui_state

    def test_extract_gui_state_from_main_window(self):
        """Test extracting GUI state from main window."""
        # Create mock main window
        main_window = Mock()
        main_window.drag_drop_label.file_path = "/test/file.pdf"

        gui_state = self.mapper.extract_gui_state_from_main_window(main_window)

        assert gui_state["pdf_path"] == "/test/file.pdf"

    def test_extract_gui_state_from_main_window_no_file(self):
        """Test extracting from main window with no file."""
        # Create mock main window with no file
        main_window = Mock()
        main_window.drag_drop_label.file_path = None

        gui_state = self.mapper.extract_gui_state_from_main_window(main_window)

        assert "pdf_path" not in gui_state

    def test_merge_gui_states(self):
        """Test merging GUI state dictionaries."""
        state1 = {"author": "Author 1", "license": "MIT"}
        state2 = {"author": "Author 2", "mod_id": "test-module"}
        state3 = {"license": "GPL", "mod_title": "Test Module"}

        merged = self.mapper.merge_gui_states(state1, state2, state3)

        assert merged["author"] == "Author 2"  # Overridden by state2
        assert merged["license"] == "GPL"  # Overridden by state3
        assert merged["mod_id"] == "test-module"  # From state2
        assert merged["mod_title"] == "Test Module"  # From state3


class TestConvenienceFunctions:
    """Test convenience functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_pdf = self.temp_dir / "test.pdf"
        self.test_pdf.write_text("fake pdf content")

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_build_config_from_gui_function(self):
        """Test the build_config_from_gui convenience function."""
        gui_state = {
            "pdf_path": str(self.test_pdf),
            "mod_id": "test-module",
            "mod_title": "Test Module",
        }

        config = build_config_from_gui(gui_state)

        assert config.pdf.resolve() == self.test_pdf.resolve()
        assert config.mod_id == "test-module"
        assert config.mod_title == "Test Module"

    def test_extract_full_gui_state_with_settings(self):
        """Test extracting full GUI state with settings dialog."""
        # Create mock main window
        main_window = Mock()
        main_window.drag_drop_label.file_path = "/test/file.pdf"

        # Create mock settings dialog
        settings_dialog = Mock()
        settings_dialog.author_edit.text.return_value = "Test Author"
        settings_dialog.license_edit.text.return_value = "MIT"

        gui_state = extract_full_gui_state(main_window, settings_dialog)

        assert gui_state["pdf_path"] == "/test/file.pdf"
        assert gui_state["author"] == "Test Author"
        assert gui_state["license"] == "MIT"

    def test_extract_full_gui_state_without_settings(self):
        """Test extracting full GUI state without settings dialog."""
        # Create mock main window
        main_window = Mock()
        main_window.drag_drop_label.file_path = "/test/file.pdf"

        gui_state = extract_full_gui_state(main_window)

        assert gui_state["pdf_path"] == "/test/file.pdf"
        assert "author" not in gui_state


class TestGuiMappingError:
    """Test GuiMappingError exception."""

    def test_gui_mapping_error_creation(self):
        """Test creating GuiMappingError with field."""
        error = GuiMappingError("Test error", field="test_field")

        assert str(error) == "Test error"
        assert error.field == "test_field"

    def test_gui_mapping_error_without_field(self):
        """Test creating GuiMappingError without field."""
        error = GuiMappingError("Test error")

        assert str(error) == "Test error"
        assert error.field is None
