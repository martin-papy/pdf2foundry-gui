"""
Page range parsing utilities for PDF processing.
"""

import re

from .validation import ValidationError

# Page range pattern for validation
PAGE_RANGE_PATTERN = re.compile(r"^(\d+(-\d+)?)(,\s*\d+(-\d+)?)*$")


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
    if not PAGE_RANGE_PATTERN.match(page_spec.strip()):
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
