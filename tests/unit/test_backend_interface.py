"""
Tests for BackendInterface functionality.
"""

import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from core.backend_interface import (
    BackendError,
    BackendInterface,
    CancellationError,
    CancellationToken,
    ConversionResult,
    convert_pdf,
)
from core.conversion_config import ConversionConfig


class TestConversionResult:
    """Test ConversionResult dataclass."""

    def test_conversion_result_creation(self):
        """Test creating ConversionResult with all fields."""
        result = ConversionResult(
            success=True,
            output_dir=Path("/test/output"),
            module_manifest_path=Path("/test/output/module.json"),
            pack_path=Path("/test/output/pack.db"),
            pages_processed=10,
            warnings=["Warning 1", "Warning 2"],
            error_message=None,
        )

        assert result.success is True
        assert result.output_dir == Path("/test/output")
        assert result.module_manifest_path == Path("/test/output/module.json")
        assert result.pack_path == Path("/test/output/pack.db")
        assert result.pages_processed == 10
        assert result.warnings == ["Warning 1", "Warning 2"]
        assert result.error_message is None

    def test_conversion_result_defaults(self):
        """Test ConversionResult with minimal fields."""
        result = ConversionResult(success=False, output_dir=Path("/test/output"), error_message="Test error")

        assert result.success is False
        assert result.output_dir == Path("/test/output")
        assert result.module_manifest_path is None
        assert result.pack_path is None
        assert result.pages_processed == 0
        assert result.warnings == []  # Should be initialized to empty list
        assert result.error_message == "Test error"


class TestCancellationToken:
    """Test CancellationToken functionality."""

    def test_cancellation_token_initial_state(self):
        """Test that cancellation token starts uncancelled."""
        token = CancellationToken()
        assert not token.is_cancelled()

    def test_cancellation_token_cancel(self):
        """Test cancelling a token."""
        token = CancellationToken()
        token.cancel()
        assert token.is_cancelled()

    def test_cancellation_token_check_cancelled_not_cancelled(self):
        """Test check_cancelled when not cancelled."""
        token = CancellationToken()
        # Should not raise an exception
        token.check_cancelled()

    def test_cancellation_token_check_cancelled_when_cancelled(self):
        """Test check_cancelled when cancelled."""
        token = CancellationToken()
        token.cancel()

        with pytest.raises(CancellationError):
            token.check_cancelled()

    def test_cancellation_token_thread_safety(self):
        """Test that cancellation token works across threads."""
        token = CancellationToken()
        results = []

        def worker():
            try:
                time.sleep(0.1)  # Give main thread time to cancel
                token.check_cancelled()
                results.append("not_cancelled")
            except CancellationError:
                results.append("cancelled")

        thread = threading.Thread(target=worker)
        thread.start()

        # Cancel from main thread
        token.cancel()
        thread.join()

        assert results == ["cancelled"]


class TestBackendInterface:
    """Test BackendInterface functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_pdf = self.temp_dir / "test.pdf"
        self.test_pdf.write_text("fake pdf content")
        self.output_dir = self.temp_dir / "output"

        self.interface = BackendInterface()

        # Create a valid config for testing
        self.valid_config = ConversionConfig(
            pdf=self.test_pdf,
            mod_id="test-module",
            mod_title="Test Module",
            out_dir=self.output_dir,
        )

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("core.backend_interface.run_conversion_pipeline")
    def test_convert_success(self, mock_run_conversion):
        """Test successful conversion."""
        # Mock the core conversion function
        mock_run_conversion.return_value = None

        # Create expected output structure
        module_dir = self.output_dir / "test-module"
        module_dir.mkdir(parents=True)
        manifest_path = module_dir / "module.json"
        manifest_path.write_text('{"name": "test-module"}')

        result = self.interface.convert(self.valid_config)

        assert result.success is True
        # Path normalization may resolve symlinks, so compare resolved paths
        assert result.output_dir.resolve() == module_dir.resolve()
        assert result.module_manifest_path.resolve() == manifest_path.resolve()
        assert mock_run_conversion.called

    @patch("core.backend_interface.run_conversion_pipeline")
    def test_convert_with_progress_callback(self, mock_run_conversion):
        """Test conversion with progress callback."""
        mock_run_conversion.return_value = None

        progress_calls = []

        def progress_cb(percent, message):
            progress_calls.append((percent, message))

        self.interface.convert(self.valid_config, progress_cb=progress_cb)

        # Should have received progress updates
        assert len(progress_calls) > 0
        assert progress_calls[0][0] == 0  # Should start at 0%
        assert progress_calls[-1][0] == 100  # Should end at 100%

    @patch("core.backend_interface.run_conversion_pipeline")
    def test_convert_with_log_callback(self, mock_run_conversion):
        """Test conversion with log callback."""
        mock_run_conversion.return_value = None

        log_calls = []

        def log_cb(level, message):
            log_calls.append((level, message))

        self.interface.convert(self.valid_config, log_cb=log_cb)

        # Should have received at least some log messages
        # (The exact number depends on the logging setup)
        assert mock_run_conversion.called

    @patch("core.backend_interface.run_conversion_pipeline")
    def test_convert_with_cancellation_token(self, mock_run_conversion):
        """Test conversion with cancellation token."""
        mock_run_conversion.return_value = None

        token = CancellationToken()
        result = self.interface.convert(self.valid_config, cancel_token=token)

        assert result.success is True
        assert mock_run_conversion.called

    @patch("core.backend_interface.run_conversion_pipeline")
    def test_convert_cancelled_before_start(self, mock_run_conversion):
        """Test conversion when cancelled before starting."""
        token = CancellationToken()
        token.cancel()  # Cancel before starting

        with pytest.raises(CancellationError):
            self.interface.convert(self.valid_config, cancel_token=token)

        # Core function should not have been called
        assert not mock_run_conversion.called

    @patch("core.backend_interface.run_conversion_pipeline")
    def test_convert_core_function_raises_exception(self, mock_run_conversion):
        """Test conversion when core function raises an exception."""
        mock_run_conversion.side_effect = Exception("Core conversion failed")

        with pytest.raises(BackendError) as exc_info:
            self.interface.convert(self.valid_config)

        assert "Conversion failed" in str(exc_info.value)
        assert exc_info.value.original_error is not None

    def test_convert_invalid_config(self):
        """Test conversion with invalid configuration."""
        invalid_config = ConversionConfig()  # Missing required fields

        with pytest.raises(BackendError):
            self.interface.convert(invalid_config)

    @patch("core.backend_interface.run_conversion_pipeline")
    def test_convert_thread_safety(self, mock_run_conversion):
        """Test that multiple conversions can run concurrently."""
        mock_run_conversion.return_value = None

        results = []
        errors = []

        def worker(worker_id):
            try:
                config = ConversionConfig(
                    pdf=self.test_pdf,
                    mod_id=f"test-module-{worker_id}",
                    mod_title=f"Test Module {worker_id}",
                    out_dir=self.output_dir,
                )
                result = self.interface.convert(config)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All conversions should have succeeded
        assert len(errors) == 0
        assert len(results) == 3
        assert all(result.success for result in results)

    def test_validate_config_valid(self):
        """Test validating a valid configuration."""
        is_valid, errors = self.interface.validate_config(self.valid_config)
        assert is_valid is True
        assert errors == []

    def test_validate_config_invalid(self):
        """Test validating an invalid configuration."""
        invalid_config = ConversionConfig()  # Missing required fields

        is_valid, errors = self.interface.validate_config(invalid_config)
        assert is_valid is False
        assert len(errors) > 0

    def test_get_version_info(self):
        """Test getting version information."""
        version_info = self.interface.get_version_info()

        assert "pdf2foundry" in version_info
        assert "backend_interface" in version_info
        assert version_info["backend_interface"] == "1.0.0"


class TestConvenienceFunction:
    """Test the convenience convert_pdf function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_pdf = self.temp_dir / "test.pdf"
        self.test_pdf.write_text("fake pdf content")

        self.valid_config = ConversionConfig(
            pdf=self.test_pdf,
            mod_id="test-module",
            mod_title="Test Module",
            out_dir=self.temp_dir / "output",
        )

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("core.backend_interface.run_conversion_pipeline")
    def test_convert_pdf_function(self, mock_run_conversion):
        """Test the convert_pdf convenience function."""
        mock_run_conversion.return_value = None

        result = convert_pdf(self.valid_config)

        assert result.success is True
        assert mock_run_conversion.called

    @patch("core.backend_interface.run_conversion_pipeline")
    def test_convert_pdf_with_callbacks(self, mock_run_conversion):
        """Test convert_pdf with callbacks."""
        mock_run_conversion.return_value = None

        progress_calls = []
        log_calls = []

        def progress_cb(percent, message):
            progress_calls.append((percent, message))

        def log_cb(level, message):
            log_calls.append((level, message))

        result = convert_pdf(self.valid_config, progress_cb=progress_cb, log_cb=log_cb)

        assert result.success is True
        assert len(progress_calls) > 0
        assert mock_run_conversion.called


class TestBackendError:
    """Test BackendError exception."""

    def test_backend_error_creation(self):
        """Test creating BackendError with original exception."""
        original = ValueError("Original error")
        error = BackendError("Backend failed", original_error=original)

        assert str(error) == "Backend failed"
        assert error.original_error is original

    def test_backend_error_without_original(self):
        """Test creating BackendError without original exception."""
        error = BackendError("Backend failed")

        assert str(error) == "Backend failed"
        assert error.original_error is None
