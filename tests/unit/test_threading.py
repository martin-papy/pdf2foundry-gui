"""
Tests for the threading system.
"""

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.conversion_config import ConversionConfig
from core.threading import ConversionWorker


class TestConversionWorker:
    """Test the ConversionWorker class."""

    def test_worker_creation(self, qtbot):
        """Test that worker can be created with valid config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "test.pdf"
            pdf_path.write_text("fake pdf content")

            config = ConversionConfig(
                pdf=pdf_path, mod_id="test-module", mod_title="Test Module", out_dir=Path(temp_dir) / "output"
            )

            worker = ConversionWorker(config)
            assert worker.config == config
            assert not worker._cancel_event.is_set()
            assert worker._throttle_ms == 50  # default

    def test_worker_cancellation(self, qtbot):
        """Test that worker cancellation works."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "test.pdf"
            pdf_path.write_text("fake pdf content")

            config = ConversionConfig(
                pdf=pdf_path, mod_id="test-module", mod_title="Test Module", out_dir=Path(temp_dir) / "output"
            )

            worker = ConversionWorker(config)

            # Test cancellation
            assert not worker._is_cancelled()
            worker.cancel()
            assert worker._is_cancelled()

    def test_progress_throttling(self, qtbot):
        """Test that progress updates are throttled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "test.pdf"
            pdf_path.write_text("fake pdf content")

            config = ConversionConfig(
                pdf=pdf_path, mod_id="test-module", mod_title="Test Module", out_dir=Path(temp_dir) / "output"
            )

            worker = ConversionWorker(config, progress_throttle_ms=100)

            # First call should emit
            assert worker._should_emit_progress()

            # Immediate second call should not emit (throttled)
            assert not worker._should_emit_progress()

            # After throttle period, should emit again
            time.sleep(0.11)  # Wait longer than throttle period
            assert worker._should_emit_progress()

    def test_progress_callback(self, qtbot):
        """Test that progress callback emits signals."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "test.pdf"
            pdf_path.write_text("fake pdf content")

            config = ConversionConfig(
                pdf=pdf_path, mod_id="test-module", mod_title="Test Module", out_dir=Path(temp_dir) / "output"
            )

            worker = ConversionWorker(config, progress_throttle_ms=0)  # No throttling

            # Use qtbot to wait for signal
            with qtbot.waitSignal(worker.progressChanged, timeout=1000) as blocker:
                worker._progress_callback(50, "Processing...")

            # Check signal arguments
            assert blocker.args == [50, "Processing..."]

    def test_log_callback(self, qtbot):
        """Test that log callback emits signals."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "test.pdf"
            pdf_path.write_text("fake pdf content")

            config = ConversionConfig(
                pdf=pdf_path, mod_id="test-module", mod_title="Test Module", out_dir=Path(temp_dir) / "output"
            )

            worker = ConversionWorker(config)

            # Use qtbot to wait for signal
            with qtbot.waitSignal(worker.logMessage, timeout=1000) as blocker:
                worker._log_callback("INFO", "Test message")

            # Check signal arguments
            assert blocker.args == ["INFO", "Test message"]

    @patch("core.threading.BackendInterface")
    def test_worker_successful_conversion(self, mock_backend_class, qtbot):
        """Test successful conversion flow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "test.pdf"
            pdf_path.write_text("fake pdf content")
            output_dir = Path(temp_dir) / "output"
            output_dir.mkdir()

            config = ConversionConfig(pdf=pdf_path, mod_id="test-module", mod_title="Test Module", out_dir=output_dir)

            # Mock successful backend result
            mock_backend = MagicMock()
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.output_dir = output_dir / "test-module"
            mock_result.module_manifest_path = output_dir / "test-module" / "module.json"
            mock_result.pack_path = None
            mock_result.pages_processed = 10
            mock_result.warnings = []

            mock_backend.convert.return_value = mock_result
            mock_backend_class.return_value = mock_backend

            worker = ConversionWorker(config)

            # Start worker and wait for completion signal
            worker.start()

            # Wait for completion signal
            with qtbot.waitSignal(worker.conversionCompleted, timeout=5000) as blocker:
                pass

            # Check result payload
            result = blocker.args[0]
            assert result["success"] is True
            assert result["mod_id"] == "test-module"
            assert result["mod_title"] == "Test Module"

    @patch("core.threading.BackendInterface")
    def test_worker_conversion_error(self, mock_backend_class, qtbot):
        """Test conversion error handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "test.pdf"
            pdf_path.write_text("fake pdf content")

            config = ConversionConfig(
                pdf=pdf_path, mod_id="test-module", mod_title="Test Module", out_dir=Path(temp_dir) / "output"
            )

            # Mock backend error
            mock_backend = MagicMock()
            mock_backend.convert.side_effect = RuntimeError("Test error")
            mock_backend_class.return_value = mock_backend

            worker = ConversionWorker(config)

            # Start worker and wait for error signal
            worker.start()

            # Wait for error signal
            with qtbot.waitSignal(worker.conversionError, timeout=5000) as blocker:
                pass

            # Check error details
            error_type, traceback_str = blocker.args
            assert error_type == "RuntimeError"
            assert "Test error" in traceback_str

    def test_set_progress_throttle(self, qtbot):
        """Test setting progress throttle dynamically."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "test.pdf"
            pdf_path.write_text("fake pdf content")

            config = ConversionConfig(
                pdf=pdf_path, mod_id="test-module", mod_title="Test Module", out_dir=Path(temp_dir) / "output"
            )

            worker = ConversionWorker(config, progress_throttle_ms=50)

            # Test setting throttle to 0 (no throttling)
            worker.setProgressThrottle(0)
            assert worker._throttle_ms == 0

            # Test setting throttle to negative value (should be clamped to 0)
            worker.setProgressThrottle(-10)
            assert worker._throttle_ms == 0

            # Test setting throttle to positive value
            worker.setProgressThrottle(200)
            assert worker._throttle_ms == 200

    def test_progress_callback_when_cancelled(self, qtbot):
        """Test that progress callbacks are ignored when cancelled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "test.pdf"
            pdf_path.write_text("fake pdf content")

            config = ConversionConfig(
                pdf=pdf_path, mod_id="test-module", mod_title="Test Module", out_dir=Path(temp_dir) / "output"
            )

            worker = ConversionWorker(config, progress_throttle_ms=0)

            # Cancel the worker first
            worker.cancel()

            # Progress callback should not emit signal when cancelled
            signal_emitted = False

            def on_progress(percent, message):
                nonlocal signal_emitted
                signal_emitted = True

            worker.progressChanged.connect(on_progress)
            worker._progress_callback(50, "Processing...")

            # Give it a moment to process
            qtbot.wait(10)
            assert not signal_emitted

    def test_log_callback_when_cancelled(self, qtbot):
        """Test that log callbacks are ignored when cancelled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "test.pdf"
            pdf_path.write_text("fake pdf content")

            config = ConversionConfig(
                pdf=pdf_path, mod_id="test-module", mod_title="Test Module", out_dir=Path(temp_dir) / "output"
            )

            worker = ConversionWorker(config)

            # Cancel the worker first
            worker.cancel()

            # Log callback should not emit signal when cancelled
            signal_emitted = False

            def on_log(level, message):
                nonlocal signal_emitted
                signal_emitted = True

            worker.logMessage.connect(on_log)
            worker._log_callback("INFO", "Test message")

            # Give it a moment to process
            qtbot.wait(10)
            assert not signal_emitted

    @patch("core.threading.BackendInterface")
    def test_worker_backend_failure_result(self, mock_backend_class, qtbot):
        """Test handling of backend failure result (not exception)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "test.pdf"
            pdf_path.write_text("fake pdf content")

            config = ConversionConfig(
                pdf=pdf_path, mod_id="test-module", mod_title="Test Module", out_dir=Path(temp_dir) / "output"
            )

            # Mock backend returning failure result (not raising exception)
            mock_backend = MagicMock()
            mock_result = MagicMock()
            mock_result.success = False
            mock_result.error_message = "Backend conversion failed"

            mock_backend.convert.return_value = mock_result
            mock_backend_class.return_value = mock_backend

            worker = ConversionWorker(config)
            worker.start()

            # Wait for error signal
            with qtbot.waitSignal(worker.conversionError, timeout=5000) as blocker:
                pass

            # Check error details
            error_type, error_msg = blocker.args
            assert error_type == "ConversionError"
            assert "Backend conversion failed" in error_msg

    @patch("core.threading.BackendInterface")
    def test_worker_backend_failure_no_message(self, mock_backend_class, qtbot):
        """Test handling of backend failure result with no error message."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "test.pdf"
            pdf_path.write_text("fake pdf content")

            config = ConversionConfig(
                pdf=pdf_path, mod_id="test-module", mod_title="Test Module", out_dir=Path(temp_dir) / "output"
            )

            # Mock backend returning failure result with no error message
            mock_backend = MagicMock()
            mock_result = MagicMock()
            mock_result.success = False
            mock_result.error_message = None

            mock_backend.convert.return_value = mock_result
            mock_backend_class.return_value = mock_backend

            worker = ConversionWorker(config)
            worker.start()

            # Wait for error signal
            with qtbot.waitSignal(worker.conversionError, timeout=5000) as blocker:
                pass

            # Check error details
            error_type, error_msg = blocker.args
            assert error_type == "ConversionError"
            assert error_msg == "Conversion failed"
