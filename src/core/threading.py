"""
Threading system for non-blocking PDF conversion operations.

This module provides a QThread-based worker system that prevents UI freezing
during long-running conversions while providing progress updates, logging,
and cancellation support.
"""

from __future__ import annotations

import logging
import threading
from time import monotonic

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot

from .backend_interface import BackendInterface
from .conversion_config import ConversionConfig

logger = logging.getLogger(__name__)


class ConversionWorker(QThread):
    """
    QThread-based worker for running PDF conversions without blocking the UI.

    This worker provides:
    - Progress updates via signals
    - Log message forwarding
    - Cooperative cancellation
    - Error handling and propagation
    - Thread-safe communication with the UI

    Signals:
        progressChanged(int, str): Progress percentage (0-100) and status message
        logMessage(str): Log message from the conversion process
        conversionCompleted(dict): Conversion completed successfully with result data
        conversionError(str, str): Conversion failed with error type and traceback
        conversionCanceled(): Conversion was canceled by user request
    """

    # Signals for thread-safe communication with UI
    progressChanged = Signal(int, str)  # percent, message
    logMessage = Signal(str, str)  # level, message
    conversionCompleted = Signal(dict)  # result payload
    conversionError = Signal(str, str)  # error_type, traceback
    conversionCanceled = Signal()  # no args

    def __init__(
        self,
        config: ConversionConfig,
        *,
        parent: QObject | None = None,
        progress_throttle_ms: int = 50,
    ) -> None:
        """
        Initialize the conversion worker.

        Args:
            config: Conversion configuration with all parameters
            parent: Parent QObject for lifetime management
            progress_throttle_ms: Minimum milliseconds between progress updates (0 = no throttling)
        """
        super().__init__(parent)

        self.config = config
        self._backend = BackendInterface()

        # Cancellation and progress state
        self._cancel_event = threading.Event()
        self._throttle_ms = max(0, progress_throttle_ms)
        self._last_progress_emit = 0.0

        # Set object name for debugging
        self.setObjectName("ConversionWorker")

    @Slot()
    def cancel(self) -> None:
        """
        Request cancellation of the conversion.

        This is thread-safe and can be called from the UI thread.
        The worker will check for cancellation periodically and emit
        conversionCanceled when it stops.
        """
        logger.info("Cancellation requested for conversion worker")
        self._cancel_event.set()

    @Slot(int)
    def setProgressThrottle(self, ms: int) -> None:
        """
        Set the minimum time between progress update emissions.

        Args:
            ms: Minimum milliseconds between progress updates (0 = no throttling)
        """
        self._throttle_ms = max(0, int(ms))

    def _should_emit_progress(self) -> bool:
        """Check if enough time has passed to emit another progress update."""
        if self._throttle_ms == 0:
            return True

        now = monotonic()
        if (now - self._last_progress_emit) * 1000 >= self._throttle_ms:
            self._last_progress_emit = now
            return True
        return False

    def _progress_callback(self, percent: int, message: str = "") -> None:
        """
        Internal progress callback for the backend.

        This is called by the backend conversion process and emits
        throttled progress signals to the UI.
        """
        if not self._cancel_event.is_set() and self._should_emit_progress():
            # Signals across threads are automatically queued by Qt
            self.progressChanged.emit(int(percent), str(message))

    def _log_callback(self, level: str, message: str) -> None:
        """
        Internal log callback for the backend.

        This forwards log messages from the conversion process to the UI.
        """
        if not self._cancel_event.is_set():
            # Emit level and message separately for UI formatting
            self.logMessage.emit(level, message)

    def _is_cancelled(self) -> bool:
        """Check if cancellation has been requested."""
        return self._cancel_event.is_set()

    def run(self) -> None:
        """
        Main worker thread execution.

        This method runs in the worker thread and performs the actual
        conversion using the backend interface. It handles all exceptions
        and ensures exactly one terminal signal is emitted.
        """
        try:
            logger.info(f"Starting conversion: {self.config.pdf} -> {self.config.out_dir}")

            # Create a cancellation token for the backend
            from .backend_interface import CancellationToken

            cancel_token = CancellationToken()

            # Connect our cancellation event to the backend token
            def check_cancel() -> None:
                if self._cancel_event.is_set():
                    cancel_token.cancel()

            # Start the conversion with callbacks
            result = self._backend.convert(
                config=self.config,
                progress_cb=self._progress_callback,
                log_cb=self._log_callback,
                cancel_token=cancel_token,
            )

            # Check final cancellation state
            if self._cancel_event.is_set():
                logger.info("Conversion was canceled")
                self.conversionCanceled.emit()
            elif result.success:
                logger.info(f"Conversion completed successfully: {result.output_dir}")

                # Create result payload for UI
                payload = {
                    "success": True,
                    "output_dir": str(result.output_dir),
                    "module_manifest_path": str(result.module_manifest_path) if result.module_manifest_path else None,
                    "pack_path": str(result.pack_path) if result.pack_path else None,
                    "pages_processed": result.pages_processed,
                    "warnings": result.warnings,
                    "input_path": str(self.config.pdf),
                    "mod_id": self.config.mod_id,
                    "mod_title": self.config.mod_title,
                }

                self.conversionCompleted.emit(payload)
            else:
                # Backend returned failure
                error_msg = result.error_message or "Conversion failed"
                logger.error(f"Conversion failed: {error_msg}")
                self.conversionError.emit("ConversionError", error_msg)

        except Exception as e:
            # Handle any unexpected exceptions
            error_type = e.__class__.__name__
            error_msg = str(e)

            # Use thread-safe logging without traceback formatting
            logger.error("Unexpected error during conversion")
            self.conversionError.emit(error_type, error_msg)


class ConversionController(QObject):
    """
    Manages the lifecycle of ConversionWorker threads.

    Provides a high-level interface for starting, canceling, and cleaning up
    conversion operations, ensuring thread safety and proper resource management.
    """

    # Signals to be emitted to the UI
    conversionStarted = Signal()
    conversionFinished = Signal()  # Emitted after cleanup
    progressChanged = Signal(int, str)
    logMessage = Signal(str, str)
    conversionCompleted = Signal(dict)
    conversionError = Signal(str, str)
    conversionCanceled = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.current_worker: ConversionWorker | None = None
        self._backend = BackendInterface()
        self._cleanup_in_progress = False
        self.setObjectName("ConversionController")
        logger.debug("ConversionController initialized.")

    def is_running(self) -> bool:
        """Check if a conversion is currently running."""
        return self.current_worker is not None and self.current_worker.isRunning()

    @Slot(ConversionConfig)
    def start_conversion(self, config: ConversionConfig) -> None:
        """
        Starts a new conversion in a worker thread.

        If a conversion is already running, it will log a warning and do nothing.
        """
        if self.current_worker and self.current_worker.isRunning():
            logger.warning("Cannot start conversion: another conversion is already running")
            return

        logger.info("Started new conversion worker")
        self.current_worker = ConversionWorker(
            config,
            parent=self,
        )
        self.current_worker.setObjectName(f"ConversionWorker-{config.mod_id}")

        # Connect worker signals to controller's public signals
        self.current_worker.progressChanged.connect(self.progressChanged, Qt.ConnectionType.QueuedConnection)
        self.current_worker.logMessage.connect(self.logMessage, Qt.ConnectionType.QueuedConnection)
        self.current_worker.conversionCompleted.connect(self.conversionCompleted, Qt.ConnectionType.QueuedConnection)
        self.current_worker.conversionError.connect(self.conversionError, Qt.ConnectionType.QueuedConnection)
        self.current_worker.conversionCanceled.connect(self.conversionCanceled, Qt.ConnectionType.QueuedConnection)

        # Connect cleanup signal with queued connection
        self.current_worker.finished.connect(self._cleanup_worker, Qt.ConnectionType.QueuedConnection)

        self.conversionStarted.emit()
        self.current_worker.start()

    @Slot()
    def cancel_conversion(self) -> None:
        """Requests cancellation of the currently running conversion."""
        if self.current_worker and self.current_worker.isRunning():
            logger.info("Requesting cancellation of current conversion")
            self.current_worker.cancel()
        else:
            logger.debug("No active conversion to cancel.")

    @Slot()
    def _cleanup_worker(self) -> None:
        """
        Cleans up the worker thread after it has finished.
        This slot is connected to the worker's finished signal.
        """
        if self._cleanup_in_progress:
            logger.debug("Cleanup already in progress, skipping redundant call.")
            return

        self._cleanup_in_progress = True
        worker_to_clean = self.current_worker
        self.current_worker = None  # Clear reference immediately

        try:
            if worker_to_clean:
                logger.debug(f"Starting cleanup for worker: {worker_to_clean.objectName()}")
                # Disconnect all signals to prevent late emissions to a potentially deleted controller
                try:
                    worker_to_clean.progressChanged.disconnect(self.progressChanged)
                    worker_to_clean.logMessage.disconnect(self.logMessage)
                    worker_to_clean.conversionCompleted.disconnect(self.conversionCompleted)
                    worker_to_clean.conversionError.disconnect(self.conversionError)
                    worker_to_clean.conversionCanceled.disconnect(self.conversionCanceled)
                    worker_to_clean.finished.disconnect(self._cleanup_worker)
                except TypeError:
                    logger.debug("Signals already disconnected or worker deleted.")

                # Ensure the thread has truly finished and resources are released
                if worker_to_clean.isRunning():
                    logger.warning(f"Worker {worker_to_clean.objectName()} is still running during cleanup. Waiting...")
                    worker_to_clean.wait(1000)  # Wait up to 1 second

                worker_to_clean.deleteLater()  # Schedule for deletion on the GUI thread's event loop
                logger.info(f"Worker {worker_to_clean.objectName()} scheduled for deletion.")
        except Exception:
            logger.exception("Error during worker cleanup.")
        finally:
            self._cleanup_in_progress = False
            self.conversionFinished.emit()
            logger.debug("Conversion cleanup finished.")

    def wait_for_completion(self, timeout_ms: int = 0) -> bool:
        """
        Waits for the current worker to finish.
        This should generally only be called during application shutdown.
        """
        if self.current_worker:
            return self.current_worker.wait(timeout_ms)
        return True

    @Slot()
    def shutdown(self, timeout_ms: int = 3000) -> None:
        """
        Gracefully shuts down any active conversion worker.
        Called when the application is about to quit.
        """
        if self.is_running():
            logger.info("Application shutting down, canceling active conversion.")
            self.cancel_conversion()
            if not self.wait_for_completion(timeout_ms):
                logger.warning(f"Worker did not finish within {timeout_ms}ms during shutdown. Forcing cleanup.")
        else:
            logger.debug("No active conversion during shutdown.")
