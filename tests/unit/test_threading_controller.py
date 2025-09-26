"""
Tests for the ConversionController class.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.conversion_config import ConversionConfig
from core.threading import ConversionController


class TestConversionController:
    """Test the ConversionController class."""

    def test_controller_creation(self):
        """Test that controller can be created."""
        controller = ConversionController()
        assert controller.current_worker is None
        assert not controller.is_running()

    def test_start_conversion(self, qtbot):
        """Test starting a conversion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir).resolve()
            pdf_path = temp_path / "test.pdf"
            pdf_path.write_text("fake pdf content")

            config = ConversionConfig(
                pdf=pdf_path, mod_id="test-module", mod_title="Test Module", out_dir=temp_path / "output"
            )

            controller = ConversionController()

            # Start conversion
            controller.start_conversion(config)

            assert controller.is_running()
            assert controller.current_worker is not None

            # Clean up
            controller.cancel_conversion()
            if controller.current_worker:
                controller.current_worker.wait(1000)

    def test_prevent_concurrent_conversions(self, qtbot):
        """Test that concurrent conversions are prevented."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "test.pdf"
            pdf_path.write_text("fake pdf content")

            config = ConversionConfig(
                pdf=pdf_path, mod_id="test-module", mod_title="Test Module", out_dir=Path(temp_dir) / "output"
            )

            controller = ConversionController()

            # Start first conversion
            controller.start_conversion(config)
            assert controller.is_running()

            # Try to start second conversion - should be ignored
            first_worker = controller.current_worker
            controller.start_conversion(config)
            # Still only one worker running
            assert controller.is_running()
            assert controller.current_worker is first_worker  # Still the first worker

            # Clean up
            controller.cancel_conversion()
            if controller.current_worker:
                controller.current_worker.wait(1000)

    def test_cancel_conversion(self, qtbot):
        """Test canceling a conversion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "test.pdf"
            pdf_path.write_text("fake pdf content")

            config = ConversionConfig(
                pdf=pdf_path, mod_id="test-module", mod_title="Test Module", out_dir=Path(temp_dir) / "output"
            )

            controller = ConversionController()

            # Start conversion
            controller.start_conversion(config)
            assert controller.is_running()

            # Cancel conversion
            controller.cancel_conversion()
            # Note: cancel_conversion doesn't return a value in the new API

            # Wait for worker to finish
            if controller.current_worker:
                controller.current_worker.wait(1000)

    def test_cancel_when_not_running(self):
        """Test canceling when no conversion is running."""
        controller = ConversionController()

        # Try to cancel when nothing is running
        controller.cancel_conversion()
        # Note: cancel_conversion doesn't return a value in the new API
        # This should not raise an error

    def test_controller_cleanup_already_in_progress(self, qtbot):
        """Test that redundant cleanup calls are ignored."""
        controller = ConversionController()

        # Set cleanup flag manually to simulate cleanup in progress
        controller._cleanup_in_progress = True

        # This should return early and not cause issues
        controller._cleanup_worker()

        # Reset flag
        controller._cleanup_in_progress = False

    def test_controller_cleanup_with_signals_already_disconnected(self, qtbot):
        """Test cleanup when signals are already disconnected."""
        controller = ConversionController()

        # Create a mock worker that raises TypeError when trying to disconnect
        mock_worker = MagicMock()
        mock_worker.objectName.return_value = "test-worker"
        mock_worker.isRunning.return_value = False

        # Mock disconnect methods to raise TypeError (simulating already disconnected signals)
        mock_worker.progressChanged.disconnect.side_effect = TypeError("Signal already disconnected")
        mock_worker.logMessage.disconnect.side_effect = TypeError("Signal already disconnected")
        mock_worker.conversionCompleted.disconnect.side_effect = TypeError("Signal already disconnected")
        mock_worker.conversionError.disconnect.side_effect = TypeError("Signal already disconnected")
        mock_worker.conversionCanceled.disconnect.side_effect = TypeError("Signal already disconnected")
        mock_worker.finished.disconnect.side_effect = TypeError("Signal already disconnected")

        controller.current_worker = mock_worker

        # Cleanup should handle TypeError gracefully and still emit conversionFinished
        with qtbot.waitSignal(controller.conversionFinished, timeout=1000):
            controller._cleanup_worker()

    def test_controller_cleanup_with_running_worker(self, qtbot):
        """Test cleanup when worker is still running."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "test.pdf"
            pdf_path.write_text("fake pdf content")

            config = ConversionConfig(
                pdf=pdf_path, mod_id="test-module", mod_title="Test Module", out_dir=Path(temp_dir) / "output"
            )

            controller = ConversionController()
            controller.start_conversion(config)

            worker = controller.current_worker
            if worker:
                # Mock isRunning to return True during cleanup
                with (
                    patch.object(worker, "isRunning", return_value=True),
                    patch.object(worker, "wait", return_value=True) as mock_wait,
                ):
                    controller._cleanup_worker()
                    mock_wait.assert_called_once_with(1000)

    def test_controller_cleanup_exception_handling(self, qtbot):
        """Test that cleanup handles exceptions gracefully."""
        controller = ConversionController()

        # Create a mock worker that raises an exception during cleanup
        mock_worker = MagicMock()
        mock_worker.objectName.return_value = "test-worker"
        mock_worker.progressChanged.disconnect.side_effect = RuntimeError("Test cleanup error")

        controller.current_worker = mock_worker

        # Cleanup should handle the exception and still emit conversionFinished
        with qtbot.waitSignal(controller.conversionFinished, timeout=1000):
            controller._cleanup_worker()

    def test_controller_wait_for_completion(self, qtbot):
        """Test waiting for worker completion."""
        controller = ConversionController()

        # Test with no worker
        assert controller.wait_for_completion() is True

        # Test with worker
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "test.pdf"
            pdf_path.write_text("fake pdf content")

            config = ConversionConfig(
                pdf=pdf_path, mod_id="test-module", mod_title="Test Module", out_dir=Path(temp_dir) / "output"
            )

            controller.start_conversion(config)

            # Mock the worker's wait method
            with patch.object(controller.current_worker, "wait", return_value=True) as mock_wait:
                result = controller.wait_for_completion(1000)
                assert result is True
                mock_wait.assert_called_once_with(1000)

            # Clean up
            controller.cancel_conversion()
            if controller.current_worker:
                controller.current_worker.wait(1000)

    def test_controller_shutdown_with_active_conversion(self, qtbot):
        """Test shutdown with active conversion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "test.pdf"
            pdf_path.write_text("fake pdf content")

            config = ConversionConfig(
                pdf=pdf_path, mod_id="test-module", mod_title="Test Module", out_dir=Path(temp_dir) / "output"
            )

            controller = ConversionController()
            controller.start_conversion(config)

            # Mock wait_for_completion to return True (successful shutdown)
            with patch.object(controller, "wait_for_completion", return_value=True):
                controller.shutdown(1000)

    def test_controller_shutdown_with_timeout(self, qtbot):
        """Test shutdown when worker doesn't finish within timeout."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "test.pdf"
            pdf_path.write_text("fake pdf content")

            config = ConversionConfig(
                pdf=pdf_path, mod_id="test-module", mod_title="Test Module", out_dir=Path(temp_dir) / "output"
            )

            controller = ConversionController()
            controller.start_conversion(config)

            # Mock wait_for_completion to return False (timeout)
            with patch.object(controller, "wait_for_completion", return_value=False):
                controller.shutdown(1000)

    def test_controller_shutdown_no_active_conversion(self, qtbot):
        """Test shutdown with no active conversion."""
        controller = ConversionController()

        # Should not raise any errors
        controller.shutdown(1000)
