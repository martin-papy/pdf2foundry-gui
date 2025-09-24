"""
PDF file validation and QMimeData parsing utilities.

This module provides reusable functions for handling PDF file validation
and extracting file paths from QMimeData objects in drag-and-drop operations.
"""

from pathlib import Path
from urllib.parse import unquote

from PySide6.QtCore import QMimeData, QMimeDatabase


def extract_local_paths_from_mimedata(mime: QMimeData) -> list[Path]:
    """
    Extract local file paths from QMimeData object.

    Handles URL decoding, deduplication, and filters out non-local URLs and directories.

    Args:
        mime: QMimeData object from drag-and-drop operation

    Returns:
        List of unique local file paths

    Raises:
        ValueError: If mime data doesn't contain URLs or contains invalid data
    """
    if not mime.hasUrls():
        raise ValueError("QMimeData does not contain URLs")

    paths = []
    seen_paths = set()

    for url in mime.urls():
        # Only process local file URLs
        if not url.isLocalFile():
            continue

        # Convert URL to local path with proper decoding
        try:
            # Get the local file path and handle percent-encoding
            local_path = unquote(url.toLocalFile())
            path = Path(local_path).resolve()

            # Skip directories
            if path.is_dir():
                continue

            # Skip if file doesn't exist
            if not path.exists():
                continue

            # Deduplicate paths
            path_str = str(path)
            if path_str not in seen_paths:
                seen_paths.add(path_str)
                paths.append(path)

        except (OSError, ValueError):
            # Skip paths that can't be resolved or are invalid
            continue

    return paths


def is_pdf_file(path: Path) -> bool:
    """
    Check if a file is a PDF based on extension and optionally MIME type.

    Args:
        path: Path to the file to check

    Returns:
        True if the file is a PDF, False otherwise
    """
    if not path.exists() or not path.is_file():
        return False

    # Check file extension (case-insensitive)
    if path.suffix.lower() != ".pdf":
        return False

    # Optional: Use QMimeDatabase for more robust detection
    try:
        mime_db = QMimeDatabase()
        mime_type = mime_db.mimeTypeForFile(str(path))
        return mime_type.name() == "application/pdf"
    except Exception:
        # Fall back to extension check if MIME detection fails
        return True


def validate_single_pdf_source(paths: list[Path]) -> tuple[Path | None, str | None]:
    """
    Validate that exactly one PDF file is provided.

    Args:
        paths: List of file paths to validate

    Returns:
        Tuple of (valid_pdf_path, error_message).
        If validation succeeds: (Path, None)
        If validation fails: (None, error_message)
    """
    if not paths:
        return None, "No files provided"

    if len(paths) > 1:
        return None, f"Multiple files provided ({len(paths)}). Please select only one PDF file."

    path = paths[0]

    if not is_pdf_file(path):
        file_type = path.suffix.lower() if path.suffix else "unknown type"
        return None, f"File is not a PDF (detected: {file_type}). Please select a PDF file."

    return path, None


def get_pdf_info(path: Path) -> dict:
    """
    Get basic information about a PDF file.

    Args:
        path: Path to the PDF file

    Returns:
        Dictionary with PDF information (size, name, etc.)
    """
    try:
        if not path.exists():
            return {"error": "File does not exist"}

        stat = path.stat()
        return {
            "name": path.name,
            "size": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "path": str(path),
            "exists": True,
        }
    except OSError as e:
        return {"error": f"Cannot access file: {e}"}
