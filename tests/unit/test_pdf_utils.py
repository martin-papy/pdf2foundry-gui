"""
Tests for PDF file validation and QMimeData parsing utilities.
"""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import QMimeData, QUrl

from core.pdf_utils import (
    extract_local_paths_from_mimedata,
    get_pdf_info,
    is_pdf_file,
    validate_single_pdf_source,
)


class TestExtractLocalPathsFromMimedata:
    """Test extract_local_paths_from_mimedata function."""

    def test_no_urls_raises_error(self):
        """Test that QMimeData without URLs raises ValueError."""
        mime = QMimeData()
        with pytest.raises(ValueError, match="does not contain URLs"):
            extract_local_paths_from_mimedata(mime)

    def test_single_valid_pdf(self, tmp_path):
        """Test extracting a single valid PDF file."""
        # Create a test PDF file
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("fake pdf content")

        # Create QMimeData with the file URL
        mime = QMimeData()
        url = QUrl.fromLocalFile(str(pdf_file))
        mime.setUrls([url])

        paths = extract_local_paths_from_mimedata(mime)
        assert len(paths) == 1
        assert paths[0] == pdf_file.resolve()

    def test_multiple_pdfs(self, tmp_path):
        """Test extracting multiple PDF files."""
        # Create test PDF files
        pdf1 = tmp_path / "test1.pdf"
        pdf2 = tmp_path / "test2.pdf"
        pdf1.write_text("fake pdf content 1")
        pdf2.write_text("fake pdf content 2")

        # Create QMimeData with multiple file URLs
        mime = QMimeData()
        urls = [QUrl.fromLocalFile(str(pdf1)), QUrl.fromLocalFile(str(pdf2))]
        mime.setUrls(urls)

        paths = extract_local_paths_from_mimedata(mime)
        assert len(paths) == 2
        assert pdf1.resolve() in paths
        assert pdf2.resolve() in paths

    def test_non_pdf_files(self, tmp_path):
        """Test extracting non-PDF files."""
        # Create test non-PDF files
        txt_file = tmp_path / "test.txt"
        jpg_file = tmp_path / "test.jpg"
        txt_file.write_text("text content")
        jpg_file.write_bytes(b"fake jpg content")

        # Create QMimeData with the file URLs
        mime = QMimeData()
        urls = [QUrl.fromLocalFile(str(txt_file)), QUrl.fromLocalFile(str(jpg_file))]
        mime.setUrls(urls)

        paths = extract_local_paths_from_mimedata(mime)
        assert len(paths) == 2  # Should include all files, filtering happens in validation

    def test_directories_filtered_out(self, tmp_path):
        """Test that directories are filtered out."""
        # Create a directory and a file
        directory = tmp_path / "test_dir"
        directory.mkdir()
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("fake pdf content")

        # Create QMimeData with both directory and file URLs
        mime = QMimeData()
        urls = [QUrl.fromLocalFile(str(directory)), QUrl.fromLocalFile(str(pdf_file))]
        mime.setUrls(urls)

        paths = extract_local_paths_from_mimedata(mime)
        assert len(paths) == 1
        assert paths[0] == pdf_file.resolve()

    def test_non_local_urls_filtered_out(self, tmp_path):
        """Test that non-local URLs are filtered out."""
        # Create a local PDF file
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("fake pdf content")

        # Create QMimeData with both local and remote URLs
        mime = QMimeData()
        local_url = QUrl.fromLocalFile(str(pdf_file))
        remote_url = QUrl("http://example.com/test.pdf")
        mime.setUrls([local_url, remote_url])

        paths = extract_local_paths_from_mimedata(mime)
        assert len(paths) == 1
        assert paths[0] == pdf_file.resolve()

    def test_nonexistent_files_filtered_out(self, tmp_path):
        """Test that non-existent files are filtered out."""
        # Create one existing file and reference one non-existing file
        existing_file = tmp_path / "existing.pdf"
        existing_file.write_text("fake pdf content")
        nonexistent_file = tmp_path / "nonexistent.pdf"

        # Create QMimeData with both URLs
        mime = QMimeData()
        urls = [QUrl.fromLocalFile(str(existing_file)), QUrl.fromLocalFile(str(nonexistent_file))]
        mime.setUrls(urls)

        paths = extract_local_paths_from_mimedata(mime)
        assert len(paths) == 1
        assert paths[0] == existing_file.resolve()

    def test_duplicate_paths_deduplicated(self, tmp_path):
        """Test that duplicate paths are deduplicated."""
        # Create a test PDF file
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("fake pdf content")

        # Create QMimeData with duplicate URLs
        mime = QMimeData()
        url = QUrl.fromLocalFile(str(pdf_file))
        mime.setUrls([url, url, url])  # Same URL multiple times

        paths = extract_local_paths_from_mimedata(mime)
        assert len(paths) == 1
        assert paths[0] == pdf_file.resolve()

    def test_percent_encoded_paths(self, tmp_path):
        """Test handling of percent-encoded file paths."""
        # Create a file with special characters in name
        pdf_file = tmp_path / "test file with spaces.pdf"
        pdf_file.write_text("fake pdf content")

        # Create QMimeData with the file URL (should be automatically encoded)
        mime = QMimeData()
        url = QUrl.fromLocalFile(str(pdf_file))
        mime.setUrls([url])

        paths = extract_local_paths_from_mimedata(mime)
        assert len(paths) == 1
        assert paths[0] == pdf_file.resolve()

    def test_invalid_url_handling(self):
        """Test that invalid URLs are handled gracefully."""
        # Create QMimeData with an invalid URL that will cause OSError/ValueError
        mime = QMimeData()
        # Create a malformed URL that should trigger the exception handler
        invalid_url = QUrl("file:///invalid\x00path/test.pdf")
        mime.setUrls([invalid_url])

        # Should not raise an exception and return empty list
        paths = extract_local_paths_from_mimedata(mime)
        assert len(paths) == 0


class TestIsPdfFile:
    """Test is_pdf_file function."""

    def test_valid_pdf_file(self, tmp_path):
        """Test valid PDF file detection."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("fake pdf content")

        with patch("core.pdf_utils.QMimeDatabase") as mock_db_class:
            mock_db = Mock()
            mock_mime_type = Mock()
            mock_mime_type.name.return_value = "application/pdf"
            mock_db.mimeTypeForFile.return_value = mock_mime_type
            mock_db_class.return_value = mock_db

            assert is_pdf_file(pdf_file) is True

    def test_non_pdf_extension(self, tmp_path):
        """Test file with non-PDF extension."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("text content")

        assert is_pdf_file(txt_file) is False

    def test_case_insensitive_extension(self, tmp_path):
        """Test case-insensitive PDF extension detection."""
        pdf_file = tmp_path / "test.PDF"
        pdf_file.write_text("fake pdf content")

        with patch("core.pdf_utils.QMimeDatabase") as mock_db_class:
            mock_db = Mock()
            mock_mime_type = Mock()
            mock_mime_type.name.return_value = "application/pdf"
            mock_db.mimeTypeForFile.return_value = mock_mime_type
            mock_db_class.return_value = mock_db

            assert is_pdf_file(pdf_file) is True

    def test_nonexistent_file(self, tmp_path):
        """Test non-existent file."""
        nonexistent = tmp_path / "nonexistent.pdf"
        assert is_pdf_file(nonexistent) is False

    def test_directory(self, tmp_path):
        """Test directory instead of file."""
        directory = tmp_path / "test.pdf"  # Directory with PDF extension
        directory.mkdir()
        assert is_pdf_file(directory) is False

    def test_mime_detection_fallback(self, tmp_path):
        """Test fallback to extension when MIME detection fails."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("fake pdf content")

        with patch("core.pdf_utils.QMimeDatabase") as mock_db_class:
            mock_db_class.side_effect = Exception("MIME detection failed")

            # Should still return True based on extension
            assert is_pdf_file(pdf_file) is True

    def test_wrong_mime_type(self, tmp_path):
        """Test file with PDF extension but wrong MIME type."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("fake pdf content")

        with patch("core.pdf_utils.QMimeDatabase") as mock_db_class:
            mock_db = Mock()
            mock_mime_type = Mock()
            mock_mime_type.name.return_value = "text/plain"  # Wrong MIME type
            mock_db.mimeTypeForFile.return_value = mock_mime_type
            mock_db_class.return_value = mock_db

            assert is_pdf_file(pdf_file) is False


class TestValidateSinglePdfSource:
    """Test validate_single_pdf_source function."""

    def test_no_files(self):
        """Test validation with no files."""
        path, error = validate_single_pdf_source([])
        assert path is None
        assert error == "No files provided"

    def test_multiple_files(self, tmp_path):
        """Test validation with multiple files."""
        pdf1 = tmp_path / "test1.pdf"
        pdf2 = tmp_path / "test2.pdf"
        pdf1.write_text("fake pdf 1")
        pdf2.write_text("fake pdf 2")

        path, error = validate_single_pdf_source([pdf1, pdf2])
        assert path is None
        assert "Multiple files provided (2)" in error

    def test_single_valid_pdf(self, tmp_path):
        """Test validation with single valid PDF."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("fake pdf content")

        with patch("core.pdf_utils.is_pdf_file", return_value=True):
            path, error = validate_single_pdf_source([pdf_file])
            assert path == pdf_file
            assert error is None

    def test_single_non_pdf_file(self, tmp_path):
        """Test validation with single non-PDF file."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("text content")

        with patch("core.pdf_utils.is_pdf_file", return_value=False):
            path, error = validate_single_pdf_source([txt_file])
            assert path is None
            assert "File is not a PDF" in error
            assert "detected: .txt" in error

    def test_file_without_extension(self, tmp_path):
        """Test validation with file without extension."""
        no_ext_file = tmp_path / "test"
        no_ext_file.write_text("content")

        with patch("core.pdf_utils.is_pdf_file", return_value=False):
            path, error = validate_single_pdf_source([no_ext_file])
            assert path is None
            assert "detected: unknown type" in error


class TestGetPdfInfo:
    """Test get_pdf_info function."""

    def test_existing_file(self, tmp_path):
        """Test getting info for existing file."""
        pdf_file = tmp_path / "test.pdf"
        content = "fake pdf content"
        pdf_file.write_text(content)

        info = get_pdf_info(pdf_file)

        assert info["name"] == "test.pdf"
        assert info["size"] == len(content.encode())
        assert info["size_mb"] == round(len(content.encode()) / (1024 * 1024), 2)
        assert info["path"] == str(pdf_file)
        assert info["exists"] is True
        assert "error" not in info

    def test_nonexistent_file(self, tmp_path):
        """Test getting info for non-existent file."""
        nonexistent = tmp_path / "nonexistent.pdf"

        info = get_pdf_info(nonexistent)

        assert info["error"] == "File does not exist"

    def test_permission_error(self, tmp_path):
        """Test handling of permission errors."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("fake pdf content")

        # Mock the stat method to simulate permission error
        with patch("core.pdf_utils.Path.stat", side_effect=OSError("Permission denied")):
            info = get_pdf_info(pdf_file)
            assert "Cannot access file" in info["error"]
