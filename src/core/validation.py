"""
Validation and normalization layer for ConversionConfig.

This module provides robust parameter validation and normalization applied
before backend execution, with structured error reporting for UI feedback.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

from .conversion_config import ConversionConfig, OcrMode, PictureDescriptionMode, TableMode


@dataclass
class ValidationError(Exception):
    """
    Structured validation error with field-specific information.

    This exception provides detailed information about validation failures
    that can be used to provide precise UI feedback to users.
    """

    field: str
    code: str
    message: str
    value: Any = None

    def __str__(self) -> str:
        """Return a user-friendly error message."""
        return f"{self.field}: {self.message}"


class ConfigValidator:
    """
    Validator for ConversionConfig instances.

    Provides comprehensive validation including filesystem checks, numeric ranges,
    enum validation, page range parsing, and cross-field constraints.
    """

    # Page range pattern: supports "1,3,5-10,15" format
    PAGE_RANGE_PATTERN = re.compile(r"^(\d+(-\d+)?)(,\d+(-\d+)?)*$")

    def validate_and_normalize(self, config: ConversionConfig) -> ConversionConfig:
        """
        Validate and normalize a ConversionConfig instance.

        Args:
            config: Configuration to validate and normalize

        Returns:
            New ConversionConfig instance with normalized values

        Raises:
            ValidationError: If validation fails
        """
        errors = []

        # Start with normalized paths
        try:
            normalized_config = config.normalize_paths()
        except Exception as e:
            errors.append(
                ValidationError(
                    field="paths", code="normalization_failed", message=f"Failed to normalize paths: {e}", value=str(e)
                )
            )
            # Use original config if normalization fails
            normalized_config = config

        # Validate required fields
        errors.extend(self._validate_required_fields(normalized_config))

        # Validate filesystem paths
        errors.extend(self._validate_filesystem(normalized_config))

        # Validate numeric ranges
        errors.extend(self._validate_numeric_ranges(normalized_config))

        # Validate enums (should already be validated by dataclass, but double-check)
        errors.extend(self._validate_enums(normalized_config))

        # Validate page ranges
        errors.extend(self._validate_page_ranges(normalized_config))

        # Validate cross-field constraints
        errors.extend(self._validate_cross_field_constraints(normalized_config))

        # If there are any errors, raise the first one
        # (In a real application, you might want to collect all errors)
        if errors:
            raise errors[0]

        return normalized_config

    def _validate_required_fields(self, config: ConversionConfig) -> list[ValidationError]:
        """Validate that all required fields are present and non-empty."""
        errors = []

        if not config.pdf:
            errors.append(
                ValidationError(field="pdf", code="required", message="PDF file path is required", value=config.pdf)
            )

        if not config.mod_id:
            errors.append(
                ValidationError(field="mod_id", code="required", message="Module ID is required", value=config.mod_id)
            )
        elif not self._is_valid_mod_id(config.mod_id):
            errors.append(
                ValidationError(
                    field="mod_id",
                    code="invalid_format",
                    message="Module ID must be lowercase with hyphens only (e.g., 'my-module')",
                    value=config.mod_id,
                )
            )

        if not config.mod_title:
            errors.append(
                ValidationError(
                    field="mod_title", code="required", message="Module title is required", value=config.mod_title
                )
            )

        return errors

    def _validate_filesystem(self, config: ConversionConfig) -> list[ValidationError]:
        """Validate filesystem paths and permissions."""
        errors = []

        # Validate input PDF exists and is readable
        if config.pdf:
            if not config.pdf.exists():
                errors.append(
                    ValidationError(
                        field="pdf",
                        code="file_not_found",
                        message=f"PDF file does not exist: {config.pdf}",
                        value=str(config.pdf),
                    )
                )
            elif not config.pdf.is_file():
                errors.append(
                    ValidationError(
                        field="pdf", code="not_a_file", message=f"Path is not a file: {config.pdf}", value=str(config.pdf)
                    )
                )
            elif not os.access(config.pdf, os.R_OK):
                errors.append(
                    ValidationError(
                        field="pdf",
                        code="not_readable",
                        message=f"PDF file is not readable: {config.pdf}",
                        value=str(config.pdf),
                    )
                )

        # Validate output directory is writable
        if config.out_dir:
            # Create parent directories if they don't exist
            try:
                config.out_dir.parent.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                errors.append(
                    ValidationError(
                        field="out_dir",
                        code="mkdir_failed",
                        message=f"Cannot create output directory parent: {e}",
                        value=str(config.out_dir),
                    )
                )

            # Check if we can write to the output directory
            if config.out_dir.exists() and not os.access(config.out_dir, os.W_OK):
                errors.append(
                    ValidationError(
                        field="out_dir",
                        code="not_writable",
                        message=f"Output directory is not writable: {config.out_dir}",
                        value=str(config.out_dir),
                    )
                )

        # Validate docling JSON path if provided
        if config.docling_json:
            parent_dir = config.docling_json.parent
            if not parent_dir.exists():
                try:
                    parent_dir.mkdir(parents=True, exist_ok=True)
                except OSError as e:
                    errors.append(
                        ValidationError(
                            field="docling_json",
                            code="mkdir_failed",
                            message=f"Cannot create docling JSON directory: {e}",
                            value=str(config.docling_json),
                        )
                    )
            elif not os.access(parent_dir, os.W_OK):
                errors.append(
                    ValidationError(
                        field="docling_json",
                        code="not_writable",
                        message=f"Docling JSON directory is not writable: {parent_dir}",
                        value=str(config.docling_json),
                    )
                )

        return errors

    def _validate_numeric_ranges(self, config: ConversionConfig) -> list[ValidationError]:
        """Validate numeric field ranges."""
        errors = []

        # Validate workers count
        if config.workers < 1:
            errors.append(
                ValidationError(
                    field="workers",
                    code="out_of_range",
                    message="Number of workers must be at least 1",
                    value=config.workers,
                )
            )
        elif config.workers > 32:  # Reasonable upper limit
            errors.append(
                ValidationError(
                    field="workers",
                    code="out_of_range",
                    message="Number of workers should not exceed 32",
                    value=config.workers,
                )
            )

        # Validate verbose level
        if config.verbose < 0:
            errors.append(
                ValidationError(
                    field="verbose", code="out_of_range", message="Verbose level must be non-negative", value=config.verbose
                )
            )
        elif config.verbose > 3:  # Typical range for verbosity
            errors.append(
                ValidationError(
                    field="verbose", code="out_of_range", message="Verbose level should not exceed 3", value=config.verbose
                )
            )

        return errors

    def _validate_enums(self, config: ConversionConfig) -> list[ValidationError]:
        """Validate enum field values."""
        errors: list[ValidationError] = []

        # These should already be validated by the dataclass, but let's be thorough
        if not isinstance(config.tables, TableMode):
            errors.append(
                ValidationError(
                    field="tables", code="invalid_enum", message=f"Invalid table mode: {config.tables}", value=config.tables
                )
            )

        if not isinstance(config.ocr, OcrMode):
            errors.append(
                ValidationError(
                    field="ocr", code="invalid_enum", message=f"Invalid OCR mode: {config.ocr}", value=config.ocr
                )
            )

        if not isinstance(config.picture_descriptions, PictureDescriptionMode):
            errors.append(
                ValidationError(
                    field="picture_descriptions",
                    code="invalid_enum",
                    message=f"Invalid picture description mode: {config.picture_descriptions}",
                    value=config.picture_descriptions,
                )
            )

        return errors

    def _validate_page_ranges(self, config: ConversionConfig) -> list[ValidationError]:
        """Validate page range specifications."""
        errors = []

        if config.pages is not None:
            # Check that all page numbers are positive
            for page in config.pages:
                if not isinstance(page, int) or page < 1:
                    errors.append(
                        ValidationError(
                            field="pages",
                            code="invalid_page_number",
                            message=f"Page numbers must be positive integers, got: {page}",
                            value=config.pages,
                        )
                    )
                    break

            # Check for duplicates
            if len(config.pages) != len(set(config.pages)):
                errors.append(
                    ValidationError(
                        field="pages", code="duplicate_pages", message="Page list contains duplicates", value=config.pages
                    )
                )

        return errors

    def _validate_cross_field_constraints(self, config: ConversionConfig) -> list[ValidationError]:
        """Validate constraints that involve multiple fields."""
        errors = []

        # If picture descriptions are enabled, VLM repo ID should be provided
        if config.picture_descriptions == PictureDescriptionMode.ON and not config.vlm_repo_id:
            errors.append(
                ValidationError(
                    field="vlm_repo_id",
                    code="required_when_picture_descriptions_on",
                    message="VLM repository ID is required when picture descriptions are enabled",
                    value=config.vlm_repo_id,
                )
            )

        # If docling_json is provided, write_docling_json should probably be False
        # (since we're reading from an existing file)
        if config.docling_json and config.write_docling_json and config.docling_json.exists():
            # This is more of a warning than an error, but let's flag it
            errors.append(
                ValidationError(
                    field="write_docling_json",
                    code="conflicting_options",
                    message="write_docling_json is enabled but docling_json file already exists",
                    value=config.write_docling_json,
                )
            )

        return errors

    def _is_valid_mod_id(self, mod_id: str) -> bool:
        """
        Check if a module ID follows the required format.

        Module IDs should be lowercase with hyphens only.
        """
        if not mod_id:
            return False

        # Check that it only contains lowercase letters, numbers, and hyphens
        if not re.match(r"^[a-z0-9-]+$", mod_id):
            return False

        # Check that it doesn't start or end with a hyphen
        if mod_id.startswith("-") or mod_id.endswith("-"):
            return False

        # Check that it doesn't have consecutive hyphens
        return "--" not in mod_id


def parse_page_range(page_spec: str) -> list[int]:
    """
    Parse a page range specification into a list of page numbers.

    Args:
        page_spec: Page specification like "1,3,5-10,15"

    Returns:
        List of page numbers (1-based)

    Raises:
        ValidationError: If the page specification is invalid
    """
    if not page_spec.strip():
        raise ValidationError(
            field="pages", code="empty_spec", message="Page specification cannot be empty", value=page_spec
        )

    # Check format with regex
    if not ConfigValidator.PAGE_RANGE_PATTERN.match(page_spec.strip()):
        raise ValidationError(
            field="pages",
            code="invalid_format",
            message="Invalid page range format. Use comma-separated numbers and ranges (e.g., '1,3,5-10')",
            value=page_spec,
        )

    pages: list[int] = []

    for part in page_spec.split(","):
        part = part.strip()

        if "-" in part:
            # Range like "5-10"
            try:
                start, end = part.split("-", 1)
                start_num = int(start)
                end_num = int(end)

                if start_num < 1 or end_num < 1:
                    raise ValidationError(
                        field="pages", code="invalid_page_number", message="Page numbers must be positive", value=page_spec
                    )

                if start_num > end_num:
                    raise ValidationError(
                        field="pages",
                        code="invalid_range",
                        message=f"Invalid range: {start_num}-{end_num} (start > end)",
                        value=page_spec,
                    )

                pages.extend(range(start_num, end_num + 1))

            except ValueError as e:
                raise ValidationError(
                    field="pages", code="invalid_number", message=f"Invalid number in range: {part}", value=page_spec
                ) from e
        else:
            # Single page number
            try:
                page_num = int(part)
                if page_num < 1:
                    raise ValidationError(
                        field="pages", code="invalid_page_number", message="Page numbers must be positive", value=page_spec
                    )
                pages.append(page_num)
            except ValueError as e:
                raise ValidationError(
                    field="pages", code="invalid_number", message=f"Invalid page number: {part}", value=page_spec
                ) from e

    # Remove duplicates and sort
    return sorted(set(pages))


def validate_and_normalize(config: ConversionConfig) -> ConversionConfig:
    """
    Convenience function to validate and normalize a ConversionConfig.

    Args:
        config: Configuration to validate and normalize

    Returns:
        New ConversionConfig instance with normalized values

    Raises:
        ValidationError: If validation fails
    """
    validator = ConfigValidator()
    return validator.validate_and_normalize(config)
