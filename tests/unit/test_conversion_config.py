"""
Tests for ConversionConfig dataclass.
"""

from pathlib import Path

import pytest

from core.conversion_config import ConversionConfig, OcrMode, PictureDescriptionMode, TableMode


class TestConversionConfig:
    """Test ConversionConfig functionality."""

    def test_from_cli_defaults(self):
        """Test creating config with CLI defaults."""
        config = ConversionConfig.from_cli_defaults()

        assert config.toc is True
        assert config.deterministic_ids is True
        assert config.out_dir == Path("dist")
        assert config.compile_pack is False
        assert config.tables == TableMode.AUTO
        assert config.ocr == OcrMode.AUTO
        assert config.picture_descriptions == PictureDescriptionMode.OFF
        assert config.workers == 1
        assert config.reflow_columns is False
        assert config.write_docling_json is False
        assert config.fallback_on_json_failure is True
        assert config.verbose == 0
        assert config.no_ml is False

    def test_from_dict_basic(self):
        """Test creating config from dictionary."""
        data = {
            "pdf": "/path/to/file.pdf",
            "mod_id": "test-module",
            "mod_title": "Test Module",
            "author": "Test Author",
            "tables": "structured",
            "ocr": "on",
            "picture_descriptions": "on",
            "workers": 4,
        }

        config = ConversionConfig.from_dict(data)

        assert config.pdf == Path("/path/to/file.pdf")
        assert config.mod_id == "test-module"
        assert config.mod_title == "Test Module"
        assert config.author == "Test Author"
        assert config.tables == TableMode.STRUCTURED
        assert config.ocr == OcrMode.ON
        assert config.picture_descriptions == PictureDescriptionMode.ON
        assert config.workers == 4

    def test_from_dict_invalid_enum(self):
        """Test that invalid enum values raise ValueError."""
        data = {
            "tables": "invalid-mode",
        }

        with pytest.raises(ValueError):
            ConversionConfig.from_dict(data)

    def test_from_dict_filters_invalid_fields(self):
        """Test that invalid field names are filtered out."""
        data = {
            "mod_id": "test",
            "invalid_field": "should_be_ignored",
            "another_invalid": 123,
        }

        config = ConversionConfig.from_dict(data)
        assert config.mod_id == "test"
        assert not hasattr(config, "invalid_field")
        assert not hasattr(config, "another_invalid")

    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = ConversionConfig(
            pdf=Path("/test.pdf"),
            mod_id="test-mod",
            mod_title="Test Module",
            tables=TableMode.STRUCTURED,
            ocr=OcrMode.OFF,
            workers=2,
        )

        result = config.to_dict()

        assert result["pdf"] == "/test.pdf"
        assert result["mod_id"] == "test-mod"
        assert result["mod_title"] == "Test Module"
        assert result["tables"] == "structured"
        assert result["ocr"] == "off"
        assert result["workers"] == 2

    def test_to_core_kwargs(self):
        """Test converting config to core function kwargs."""
        config = ConversionConfig(
            pdf=Path("/test.pdf"),
            mod_id="test-mod",
            mod_title="Test Module",
            author="Test Author",
            tables=TableMode.IMAGE_ONLY,
            ocr=OcrMode.AUTO,
            picture_descriptions=PictureDescriptionMode.ON,
            workers=3,
            compile_pack=True,
        )

        kwargs = config.to_core_kwargs()

        assert kwargs["pdf"] == Path("/test.pdf")
        assert kwargs["mod_id"] == "test-mod"
        assert kwargs["mod_title"] == "Test Module"
        assert kwargs["author"] == "Test Author"
        assert kwargs["pack_name"] == "test-mod-journals"  # Default computed
        assert kwargs["tables"] == "image-only"
        assert kwargs["ocr"] == "auto"
        assert kwargs["picture_descriptions"] == "on"
        assert kwargs["workers"] == 3
        assert kwargs["compile_pack_now"] is True

    def test_to_core_kwargs_custom_pack_name(self):
        """Test that custom pack_name is preserved."""
        config = ConversionConfig(
            mod_id="test-mod",
            pack_name="custom-pack-name",
        )

        kwargs = config.to_core_kwargs()
        assert kwargs["pack_name"] == "custom-pack-name"

    def test_validate_required_fields_all_present(self):
        """Test validation when all required fields are present."""
        config = ConversionConfig(
            pdf=Path("/test.pdf"),
            mod_id="test-mod",
            mod_title="Test Module",
        )

        missing = config.validate_required_fields()
        assert missing == []

    def test_validate_required_fields_missing(self):
        """Test validation when required fields are missing."""
        config = ConversionConfig()

        missing = config.validate_required_fields()
        assert set(missing) == {"pdf", "mod_id", "mod_title"}

    def test_validate_required_fields_partial(self):
        """Test validation when some required fields are missing."""
        config = ConversionConfig(
            pdf=Path("/test.pdf"),
            mod_title="Test Module",
        )

        missing = config.validate_required_fields()
        assert missing == ["mod_id"]

    def test_normalize_paths(self):
        """Test path normalization."""
        config = ConversionConfig(
            pdf=Path("~/test.pdf"),
            out_dir=Path("$HOME/output"),
            docling_json=Path("./cache.json"),
        )

        normalized = config.normalize_paths()

        # Paths should be absolute and expanded
        assert normalized.pdf.is_absolute()
        assert normalized.out_dir.is_absolute()
        assert normalized.docling_json.is_absolute()

        # Original config should be unchanged
        assert config.pdf == Path("~/test.pdf")
        assert config.out_dir == Path("$HOME/output")

    def test_round_trip_serialization(self):
        """Test that to_dict -> from_dict preserves data."""
        original = ConversionConfig(
            pdf=Path("/test.pdf"),
            mod_id="test-mod",
            mod_title="Test Module",
            tables=TableMode.STRUCTURED,
            ocr=OcrMode.ON,
            picture_descriptions=PictureDescriptionMode.OFF,
            pages=[1, 2, 3],
            workers=4,
        )

        # Round trip
        data = original.to_dict()
        restored = ConversionConfig.from_dict(data)

        assert restored.pdf == original.pdf
        assert restored.mod_id == original.mod_id
        assert restored.mod_title == original.mod_title
        assert restored.tables == original.tables
        assert restored.ocr == original.ocr
        assert restored.picture_descriptions == original.picture_descriptions
        assert restored.pages == original.pages
        assert restored.workers == original.workers


class TestEnums:
    """Test enum definitions."""

    def test_table_mode_values(self):
        """Test TableMode enum values."""
        assert TableMode.STRUCTURED.value == "structured"
        assert TableMode.AUTO.value == "auto"
        assert TableMode.IMAGE_ONLY.value == "image-only"

    def test_ocr_mode_values(self):
        """Test OcrMode enum values."""
        assert OcrMode.AUTO.value == "auto"
        assert OcrMode.ON.value == "on"
        assert OcrMode.OFF.value == "off"

    def test_picture_description_mode_values(self):
        """Test PictureDescriptionMode enum values."""
        assert PictureDescriptionMode.ON.value == "on"
        assert PictureDescriptionMode.OFF.value == "off"
