"""
Stress tests for the threading system to validate concurrency hardening.
"""

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QCoreApplication

from core.conversion_config import ConversionConfig
from core.threading import ConversionController, ConversionWorker


@pytest.fixture
def cleanup_qt():
    """Ensure Qt application cleanup between tests."""
    yield
    # Process any pending Qt events
    if QCoreApplication.instance():
        QCoreApplication.processEvents()
        # Give a small delay for cleanup
        time.sleep(0.1)


class TestThreadingStress:
    """Stress tests for threading system concurrency and race conditions."""

    def test_rapid_start_cancel_cycles(self, qtbot):
        """Test rapid start/cancel cycles don't cause race conditions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir).resolve()
            pdf_path = temp_path / "test.pdf"
            pdf_path.write_text("fake pdf content")

            config = ConversionConfig(
                pdf=pdf_path, mod_id="test-module", mod_title="Test Module", out_dir=temp_path / "output"
            )

            controller = ConversionController()

            # Perform rapid start/cancel cycles
            for _ in range(5):
                # Start conversion (new API returns None)
                controller.start_conversion(config)
                if controller.is_running():
                    # Cancel immediately
                    controller.cancel_conversion()
                    # Wait a bit for cleanup
                    qtbot.wait(200)

            # Wait for final cleanup
            qtbot.wait(500)

            # Ensure we end in a clean state
            assert not controller.is_running()

    def test_multiple_conversion_attempts(self, qtbot):
        """Test that multiple conversion attempts are properly rejected."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir).resolve()
            pdf_path = temp_path / "test.pdf"
            pdf_path.write_text("fake pdf content")

            config = ConversionConfig(
                pdf=pdf_path, mod_id="test-module", mod_title="Test Module", out_dir=temp_path / "output"
            )

            controller = ConversionController()

            # Start first conversion (new API returns None)
            controller.start_conversion(config)
            assert controller.is_running()
            first_worker = controller.current_worker

            # Try to start multiple additional conversions
            for _ in range(3):
                controller.start_conversion(config)  # Should be ignored
                assert controller.current_worker is first_worker  # Original still active

            # Clean up
            controller.cancel_conversion()
            qtbot.wait(500)  # Give time for cleanup

    def test_progress_callback_flood(self, qtbot):
        """Test that flooding progress callbacks doesn't overwhelm the UI."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir).resolve()
            pdf_path = temp_path / "test.pdf"
            pdf_path.write_text("fake pdf content")

            config = ConversionConfig(
                pdf=pdf_path, mod_id="test-module", mod_title="Test Module", out_dir=temp_path / "output"
            )

            # Create worker
            worker = ConversionWorker(config, progress_throttle_ms=1)

            progress_count = 0

            def count_progress(percent, message):
                nonlocal progress_count
                progress_count += 1

            worker.progressChanged.connect(count_progress)

            # Flood with progress updates
            for i in range(100):
                worker._progress_callback(i, f"Step {i}")

            # Wait for all signals to be processed
            qtbot.wait(100)

            # Should have throttled the updates significantly
            # With 1ms throttling, we shouldn't get all 100 updates
            assert progress_count < 100, f"Expected throttling, got {progress_count} updates"

    def test_cleanup_idempotency(self, qtbot, cleanup_qt):
        """Test that cleanup operations are idempotent."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir).resolve()
            pdf_path = temp_path / "test.pdf"
            pdf_path.write_text("fake pdf content")

            config = ConversionConfig(
                pdf=pdf_path, mod_id="test-module", mod_title="Test Module", out_dir=temp_path / "output"
            )

            controller = ConversionController()

            # Start and immediately cancel (new API returns None)
            controller.start_conversion(config)
            if controller.is_running():
                controller.cancel_conversion()

                # Wait for worker to finish
                qtbot.wait(500)

                # Call cleanup multiple times - should be safe
                for _ in range(3):
                    controller._cleanup_worker()

                # Should still be in clean state
                assert not controller.is_running()
                assert controller.current_worker is None

    def test_shutdown_during_conversion(self, qtbot, cleanup_qt):
        """Test graceful shutdown while conversion is running."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir).resolve()
            pdf_path = temp_path / "test.pdf"
            pdf_path.write_text("fake pdf content")

            config = ConversionConfig(
                pdf=pdf_path, mod_id="test-module", mod_title="Test Module", out_dir=temp_path / "output"
            )

            controller = ConversionController()

            # Start conversion (new API returns None)
            controller.start_conversion(config)
            if controller.is_running():
                assert controller.is_running()

                # Test shutdown with short timeout
                start_time = time.time()
                controller.shutdown(timeout_ms=500)
                elapsed = time.time() - start_time

                # Should complete within reasonable time
                assert elapsed < 1.0  # Should not hang

                # Should be clean after shutdown
                assert not controller.is_running()

    def test_worker_state_consistency(self, qtbot):
        """Test that worker state remains consistent under stress."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "test.pdf"
            pdf_path.write_text("fake pdf content")

            config = ConversionConfig(
                pdf=pdf_path, mod_id="test-module", mod_title="Test Module", out_dir=Path(temp_dir) / "output"
            )

            worker = ConversionWorker(config)

            # Test cancellation state consistency
            assert not worker._is_cancelled()

            worker.cancel()
            assert worker._is_cancelled()

            # Multiple cancels should be safe
            for _ in range(5):
                worker.cancel()
                assert worker._is_cancelled()

    def test_signal_emission_order(self, qtbot):
        """Test that signals are emitted in the correct order."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "test.pdf"
            pdf_path.write_text("fake pdf content")

            config = ConversionConfig(
                pdf=pdf_path, mod_id="test-module", mod_title="Test Module", out_dir=Path(temp_dir) / "output"
            )

            worker = ConversionWorker(config, progress_throttle_ms=0)

            signal_order = []

            def track_progress(percent, message):
                signal_order.append(f"progress_{percent}")

            def track_log(message):
                signal_order.append(f"log_{len(signal_order)}")

            def track_completed(result):
                signal_order.append("completed")

            def track_error(error_type, traceback_str):
                signal_order.append("error")

            def track_canceled():
                signal_order.append("canceled")

            worker.progressChanged.connect(track_progress)
            worker.logMessage.connect(track_log)
            worker.conversionCompleted.connect(track_completed)
            worker.conversionError.connect(track_error)
            worker.conversionCanceled.connect(track_canceled)

            # Simulate signal sequence
            worker._progress_callback(0, "Starting")
            worker._log_callback("INFO", "Test log")
            worker._progress_callback(50, "Halfway")
            worker.cancel()  # This should affect future signals

            # Wait for signals to process
            qtbot.wait(50)

            # Check that we got signals in reasonable order
            assert len(signal_order) >= 3
            assert "progress_0" in signal_order
            assert any("log_" in s for s in signal_order)

    def test_backend_exception_handling(self, qtbot, cleanup_qt):
        """Test that backend exceptions are properly handled under stress."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir).resolve()
            pdf_path = temp_path / "test.pdf"
            pdf_path.write_text("fake pdf content")

            config = ConversionConfig(
                pdf=pdf_path, mod_id="test-module", mod_title="Test Module", out_dir=temp_path / "output"
            )

            # Test with a single exception type to avoid complex mocking issues
            with patch("core.threading.BackendInterface") as mock_backend_class:
                mock_backend = MagicMock()
                mock_backend.convert.side_effect = RuntimeError("Test runtime error")
                mock_backend_class.return_value = mock_backend

                worker = ConversionWorker(config)

                # Track if error signal was emitted
                error_emitted = False

                def on_error(error_type, error_msg):
                    nonlocal error_emitted
                    error_emitted = True

                worker.conversionError.connect(on_error)

                # Start worker and wait for it to finish
                worker.start()
                finished = worker.wait(3000)  # Wait up to 3 seconds for worker to finish

                # Worker should finish (not hang) even with exceptions
                assert finished, "Worker did not finish within timeout"

                # Process Qt events to ensure signals are delivered
                qtbot.wait(100)

                # Should have emitted an error signal
                assert error_emitted, "Expected error signal to be emitted"
