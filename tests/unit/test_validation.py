"""
Tests for validation and normalization functionality.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from core.conversion_config import ConversionConfig, PictureDescriptionMode
from core.validation import ConfigValidator, ValidationError, parse_page_range, validate_and_normalize


class TestValidationError:
    """Test ValidationError exception."""

    def test_validation_error_creation(self):
        """Test creating ValidationError with all fields."""
        error = ValidationError(field="test_field", code="test_code", message="Test message", value="test_value")

        assert error.field == "test_field"
        assert error.code == "test_code"
        assert error.message == "Test message"
        assert error.value == "test_value"
        assert str(error) == "test_field: Test message"

    def test_validation_error_without_value(self):
        """Test creating ValidationError without value."""
        error = ValidationError(field="test_field", code="test_code", message="Test message")

        assert error.value is None


class TestConfigValidator:
    """Test ConfigValidator functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ConfigValidator()
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_pdf = self.temp_dir / "test.pdf"
        self.test_pdf.write_text("fake pdf content")

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate_required_fields_all_present(self):
        """Test validation when all required fields are present."""
        config = ConversionConfig(pdf=self.test_pdf, mod_id="test-module", mod_title="Test Module")

        result = self.validator.validate_and_normalize(config)
        # Path normalization may resolve symlinks, so compare resolved paths
        assert result.pdf.resolve() == self.test_pdf.resolve()
        assert result.mod_id == "test-module"
        assert result.mod_title == "Test Module"

    def test_validate_required_fields_missing_pdf(self):
        """Test validation when PDF is missing."""
        config = ConversionConfig(mod_id="test-module", mod_title="Test Module")

        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate_and_normalize(config)

        assert exc_info.value.field == "pdf"
        assert exc_info.value.code == "required"

    def test_validate_required_fields_missing_mod_id(self):
        """Test validation when mod_id is missing."""
        config = ConversionConfig(pdf=self.test_pdf, mod_title="Test Module")

        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate_and_normalize(config)

        assert exc_info.value.field == "mod_id"
        assert exc_info.value.code == "required"

    def test_validate_required_fields_missing_mod_title(self):
        """Test validation when mod_title is missing."""
        config = ConversionConfig(pdf=self.test_pdf, mod_id="test-module")

        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate_and_normalize(config)

        assert exc_info.value.field == "mod_title"
        assert exc_info.value.code == "required"

    def test_validate_mod_id_format_valid(self):
        """Test validation of valid mod_id formats."""
        valid_ids = ["simple", "with-hyphens", "with123numbers", "a", "very-long-module-name-with-many-parts"]

        for mod_id in valid_ids:
            config = ConversionConfig(pdf=self.test_pdf, mod_id=mod_id, mod_title="Test Module")

            # Should not raise an exception
            result = self.validator.validate_and_normalize(config)
            assert result.mod_id == mod_id

    def test_validate_mod_id_format_invalid(self):
        """Test validation of invalid mod_id formats."""
        invalid_ids = [
            "With-Capitals",
            "with_underscores",
            "with spaces",
            "with.dots",
            "-starts-with-hyphen",
            "ends-with-hyphen-",
            "has--double-hyphens",
            "special@chars",
            "",
        ]

        for mod_id in invalid_ids:
            config = ConversionConfig(pdf=self.test_pdf, mod_id=mod_id, mod_title="Test Module")

            with pytest.raises(ValidationError) as exc_info:
                self.validator.validate_and_normalize(config)

            assert exc_info.value.field in ["mod_id"]
            assert exc_info.value.code in ["required", "invalid_format"]

    def test_validate_filesystem_pdf_not_exists(self):
        """Test validation when PDF file doesn't exist."""
        non_existent_pdf = self.temp_dir / "nonexistent.pdf"
        config = ConversionConfig(pdf=non_existent_pdf, mod_id="test-module", mod_title="Test Module")

        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate_and_normalize(config)

        assert exc_info.value.field == "pdf"
        assert exc_info.value.code == "file_not_found"

    def test_validate_filesystem_pdf_not_file(self):
        """Test validation when PDF path is not a file."""
        config = ConversionConfig(
            pdf=self.temp_dir,  # Directory instead of file
            mod_id="test-module",
            mod_title="Test Module",
        )

        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate_and_normalize(config)

        assert exc_info.value.field == "pdf"
        assert exc_info.value.code == "not_a_file"

    @patch("os.access")
    def test_validate_filesystem_pdf_not_readable(self, mock_access):
        """Test validation when PDF file is not readable."""
        mock_access.return_value = False

        config = ConversionConfig(pdf=self.test_pdf, mod_id="test-module", mod_title="Test Module")

        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate_and_normalize(config)

        assert exc_info.value.field == "pdf"
        assert exc_info.value.code == "not_readable"

    def test_validate_numeric_ranges_workers_too_low(self):
        """Test validation when workers count is too low."""
        config = ConversionConfig(pdf=self.test_pdf, mod_id="test-module", mod_title="Test Module", workers=0)

        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate_and_normalize(config)

        assert exc_info.value.field == "workers"
        assert exc_info.value.code == "out_of_range"

    def test_validate_numeric_ranges_workers_too_high(self):
        """Test validation when workers count is too high."""
        config = ConversionConfig(pdf=self.test_pdf, mod_id="test-module", mod_title="Test Module", workers=100)

        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate_and_normalize(config)

        assert exc_info.value.field == "workers"
        assert exc_info.value.code == "out_of_range"

    def test_validate_numeric_ranges_verbose_negative(self):
        """Test validation when verbose level is negative."""
        config = ConversionConfig(pdf=self.test_pdf, mod_id="test-module", mod_title="Test Module", verbose=-1)

        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate_and_normalize(config)

        assert exc_info.value.field == "verbose"
        assert exc_info.value.code == "out_of_range"

    def test_validate_page_ranges_invalid_page_number(self):
        """Test validation when page list contains invalid numbers."""
        config = ConversionConfig(
            pdf=self.test_pdf,
            mod_id="test-module",
            mod_title="Test Module",
            pages=[1, 0, 3],  # 0 is invalid
        )

        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate_and_normalize(config)

        assert exc_info.value.field == "pages"
        assert exc_info.value.code == "invalid_page_number"

    def test_validate_page_ranges_duplicates(self):
        """Test validation when page list contains duplicates."""
        config = ConversionConfig(
            pdf=self.test_pdf,
            mod_id="test-module",
            mod_title="Test Module",
            pages=[1, 2, 2, 3],  # Duplicate 2
        )

        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate_and_normalize(config)

        assert exc_info.value.field == "pages"
        assert exc_info.value.code == "duplicate_pages"

    def test_validate_cross_field_picture_descriptions_without_vlm(self):
        """Test validation when picture descriptions are on but VLM repo ID is missing."""
        config = ConversionConfig(
            pdf=self.test_pdf,
            mod_id="test-module",
            mod_title="Test Module",
            picture_descriptions=PictureDescriptionMode.ON,
            vlm_repo_id=None,
        )

        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate_and_normalize(config)

        assert exc_info.value.field == "vlm_repo_id"
        assert exc_info.value.code == "required_when_picture_descriptions_on"

    def test_validate_cross_field_picture_descriptions_with_vlm(self):
        """Test validation when picture descriptions are on and VLM repo ID is provided."""
        config = ConversionConfig(
            pdf=self.test_pdf,
            mod_id="test-module",
            mod_title="Test Module",
            picture_descriptions=PictureDescriptionMode.ON,
            vlm_repo_id="microsoft/Florence-2-base",
        )

        # Should not raise an exception
        result = self.validator.validate_and_normalize(config)
        assert result.picture_descriptions == PictureDescriptionMode.ON
        assert result.vlm_repo_id == "microsoft/Florence-2-base"


class TestParsePageRange:
    """Test page range parsing functionality."""

    def test_parse_single_page(self):
        """Test parsing single page number."""
        result = parse_page_range("5")
        assert result == [5]

    def test_parse_multiple_pages(self):
        """Test parsing multiple page numbers."""
        result = parse_page_range("1,3,5")
        assert result == [1, 3, 5]

    def test_parse_page_range(self):
        """Test parsing page ranges."""
        result = parse_page_range("5-10")
        assert result == [5, 6, 7, 8, 9, 10]

    def test_parse_mixed_format(self):
        """Test parsing mixed pages and ranges."""
        result = parse_page_range("1,3,5-7,10")
        assert result == [1, 3, 5, 6, 7, 10]

    def test_parse_with_duplicates(self):
        """Test that duplicates are removed."""
        result = parse_page_range("1,3,5-7,6")
        assert result == [1, 3, 5, 6, 7]  # Sorted and deduplicated

    def test_parse_empty_spec(self):
        """Test parsing empty specification."""
        with pytest.raises(ValidationError) as exc_info:
            parse_page_range("")

        assert exc_info.value.field == "pages"
        assert exc_info.value.code == "empty_spec"

    def test_parse_invalid_format(self):
        """Test parsing invalid format."""
        invalid_specs = ["1-", "-5", "1--5", "1,", ",5", "1,2-", "abc", "1,abc,3"]

        for spec in invalid_specs:
            with pytest.raises(ValidationError) as exc_info:
                parse_page_range(spec)

            assert exc_info.value.field == "pages"
            assert exc_info.value.code in ["invalid_format", "invalid_number"]

    def test_parse_invalid_range(self):
        """Test parsing invalid ranges."""
        with pytest.raises(ValidationError) as exc_info:
            parse_page_range("10-5")  # Start > end

        assert exc_info.value.field == "pages"
        assert exc_info.value.code == "invalid_range"

    def test_parse_zero_or_negative_pages(self):
        """Test parsing zero or negative page numbers."""
        invalid_specs = ["0", "-1", "1,0,3", "5--1"]

        for spec in invalid_specs:
            with pytest.raises(ValidationError) as exc_info:
                parse_page_range(spec)

            assert exc_info.value.field == "pages"
            assert exc_info.value.code in ["invalid_page_number", "invalid_format", "invalid_number"]


class TestValidateAndNormalize:
    """Test the convenience function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_pdf = self.temp_dir / "test.pdf"
        self.test_pdf.write_text("fake pdf content")

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_convenience_function(self):
        """Test the validate_and_normalize convenience function."""
        config = ConversionConfig(pdf=self.test_pdf, mod_id="test-module", mod_title="Test Module")

        result = validate_and_normalize(config)
        # Path normalization may resolve symlinks, so compare resolved paths
        assert result.pdf.resolve() == self.test_pdf.resolve()
        assert result.mod_id == "test-module"
        assert result.mod_title == "Test Module"

    def test_convenience_function_with_error(self):
        """Test the convenience function with validation error."""
        config = ConversionConfig()  # Missing required fields

        with pytest.raises(ValidationError):
            validate_and_normalize(config)
