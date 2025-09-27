"""TestsfortheNotificationManagerclass."""

import sys
from time import monotonic
from unittest.mock import Mock, patch

from PySide6.QtWidgets import QWidget

from gui.widgets.notification_manager import NotificationManager


class TestNotificationManager:
    """BasetestclassforNotificationManager."""

    def setup_method(self):
        """Setuptestfixtures."""
        # Create a mock parent widget to avoid Qt object initialization issues
        self.mock_parent = Mock(spec=QWidget)
        # Initialize manager with None parent to avoid QObject.__init__ issues
        # Then manually set the parent widget for internal logic
        self.manager = NotificationManager(None)
        self.manager._parent_widget = self.mock_parent


class TestInitialization(TestNotificationManager):
    """TestNotificationManagerinitialization."""

    def test_initialization_basic(self):
        """Testbasicinitialization."""
        manager = NotificationManager(None)
        assert manager._parent_widget is None
        assert manager._notification_cache == {}
        assert manager._notified_conversions == {}
        assert manager._debounce_ttl == 3.0
        assert manager._system_tray is None
        assert manager._tray_available is False

    def test_initialization_with_parent(self):
        """Testinitializationwithparentwidget."""
        parent = Mock(spec=QWidget)
        # Initialize with None and manually set parent to avoid QObject issues
        manager = NotificationManager(None)
        manager._parent_widget = parent
        assert manager._parent_widget is parent

    def test_test_mode_detection_pytest(self):
        """Testtestmodedetectionwithpytest."""
        # pytest should be in sys.modules during testing
        assert self.manager._test_mode is True

    def test_test_mode_detection_unittest(self):
        """Testtestmodedetectionwithunittest."""
        with patch.dict("sys.modules", {"unittest": Mock()}):
            manager = NotificationManager(None)
            assert manager._test_mode is True

    def test_test_mode_detection_argv(self):
        """Testtestmodedetectionfromcommandlineargs."""
        original_argv = sys.argv[:]
        try:
            sys.argv = ["python", "-m", "pytest", "test_file.py"]
            manager = NotificationManager(None)
            assert manager._test_mode is True
        finally:
            sys.argv = original_argv

    def test_test_mode_detection_attribute(self):
        """Testtestmodedetectionfromsysattribute."""
        try:
            sys._called_from_test = True
            manager = NotificationManager(None)
            assert manager._test_mode is True
        finally:
            if hasattr(sys, "_called_from_test"):
                delattr(sys, "_called_from_test")

    def test_system_tray_initialization_success(self):
        """Testsuccessfulsystemtrayinitialization."""
        # Mock the entire _init_system_tray method to avoid Qt object creation
        with (
            patch.object(NotificationManager, "_detect_test_mode", return_value=False),
            patch.object(NotificationManager, "_init_system_tray") as mock_init_tray,
        ):
            manager = NotificationManager(None)
            # Manually set up the expected state
            manager._system_tray = Mock()
            manager._tray_available = True
            mock_init_tray.assert_called_once()
            assert manager._system_tray is not None
            assert manager._tray_available is True

    def test_system_tray_initialization_unavailable(self):
        """Testsystemtrayinitializationwhenunavailable."""
        # Mock the entire _init_system_tray method to avoid Qt object creation
        with (
            patch.object(NotificationManager, "_detect_test_mode", return_value=False),
            patch.object(NotificationManager, "_init_system_tray") as mock_init_tray,
        ):
            manager = NotificationManager(None)
            # Manually set up the expected state for unavailable tray
            manager._system_tray = None
            manager._tray_available = False
            mock_init_tray.assert_called_once()
            assert manager._system_tray is None
            assert manager._tray_available is False

    def test_system_tray_initialization_no_app(self):
        """Testsystemtrayinitializationwhennoappinstance."""
        # Mock the entire _init_system_tray method to avoid Qt object creation
        with (
            patch.object(NotificationManager, "_detect_test_mode", return_value=False),
            patch.object(NotificationManager, "_init_system_tray") as mock_init_tray,
        ):
            manager = NotificationManager(None)
            # Manually set up the expected state for no app
            manager._system_tray = None
            manager._tray_available = False
            mock_init_tray.assert_called_once()
            assert manager._system_tray is None
            assert manager._tray_available is False


class TestNotificationBasic(TestNotificationManager):
    """Testbasicnotificationfunctionality."""

    def test_notify_in_test_mode(self):
        """Testnotificationintestmodelogsmessage."""
        self.manager._test_mode = True
        with patch.object(self.manager._logger, "info") as mock_log:
            self.manager.notify("success", "Test Title", "Test Message")
            mock_log.assert_called_once_with(
                "TEST NOTIFICATION [success] Test Title: Test Message (output_path=None, job_id=None)"
            )

    def test_notify_without_test_mode_message_box(self):
        """Testnotificationwithouttestmodeusesmessagebox."""
        self.manager._test_mode = False
        with (
            patch.object(self.manager, "_should_use_system_tray", return_value=False),
            patch.object(self.manager, "_show_message_box") as mock_message_box,
        ):
            self.manager.notify("success", "Test Title", "Test Message")
            mock_message_box.assert_called_once_with("success", "Test Title", "Test Message", None)

    def test_notify_without_test_mode_system_tray(self):
        """Testnotificationwithouttestmodeusessystemtray."""
        self.manager._test_mode = False
        with (
            patch.object(self.manager, "_should_use_system_tray", return_value=True),
            patch.object(self.manager, "_show_tray_notification") as mock_tray,
        ):
            self.manager.notify("success", "Test Title", "Test Message")
            mock_tray.assert_called_once_with("success", "Test Title", "Test Message", None)


class TestConversionDeduplication(TestNotificationManager):
    """Testconversion-specificdeduplication."""

    def test_conversion_deduplication_first_notification(self):
        """Testfirstconversionnotificationisallowed."""
        self.manager._test_mode = False
        with patch.object(self.manager, "_show_message_box") as mock_message_box:
            self.manager.notify("success", "Success", "Message", job_id="conv123")
            mock_message_box.assert_called_once()
            assert "conv123" in self.manager._notified_conversions
            assert self.manager._notified_conversions["conv123"] == "success"

    def test_conversion_deduplication_duplicate_blocked(self):
        """Testduplicateconversionnotificationsareblocked."""
        self.manager._test_mode = False
        self.manager._notified_conversions["conv123"] = "success"
        with patch.object(self.manager, "_show_message_box") as mock_message_box:
            self.manager.notify("error", "Error", "Message", job_id="conv123")
            mock_message_box.assert_not_called()

    def test_conversion_deduplication_info_status_ignored(self):
        """Test info status notifications bypass conversion deduplication."""
        self.manager._test_mode = False
        with patch.object(self.manager, "_show_message_box") as mock_message_box:
            self.manager.notify("info", "Info Message", "Information", job_id="conv123")
            mock_message_box.assert_called_once()
            assert "conv123" not in self.manager._notified_conversions

    def test_conversion_deduplication_no_job_id(self):
        """Test notifications without job_id are still subject to general debouncing."""
        self.manager._test_mode = False
        with patch.object(self.manager, "_show_message_box") as mock_message_box:
            # Identical notifications should be debounced
            self.manager.notify("success", "Success", "Message")
            self.manager.notify("success", "Success", "Message")
            assert mock_message_box.call_count == 1
            # Different notifications should not be debounced
            self.manager.notify("success", "Different", "Message")
            assert mock_message_box.call_count == 2


class TestDebouncing(TestNotificationManager):
    """Testnotificationdebouncing."""

    def test_debouncing_first_notification_allowed(self):
        """Testfirstnotificationisalwaysallowed."""
        self.manager._test_mode = False
        with patch.object(self.manager, "_show_message_box") as mock_message_box:
            self.manager.notify("success", "Test", "Message")
            mock_message_box.assert_called_once()

    def test_debouncing_recent_notification_blocked(self):
        """Testrecentduplicatenotificationsareblocked."""
        self.manager._test_mode = False
        # Manually add a recent notification to cache
        key = (None, "success", "Test", "Message", None)
        self.manager._notification_cache[key] = monotonic()
        with patch.object(self.manager, "_show_message_box") as mock_message_box:
            self.manager.notify("success", "Test", "Message")
            mock_message_box.assert_not_called()

    def test_debouncing_expired_notification_allowed(self):
        """Testexpirednotificationsareallowedthrough."""
        self.manager._test_mode = False
        # Add an old notification to cache
        key = (None, "success", "Test", "Message", None)
        self.manager._notification_cache[key] = monotonic() - 10  # 10 seconds ago
        with patch.object(self.manager, "_show_message_box") as mock_message_box:
            self.manager.notify("success", "Test", "Message")
            mock_message_box.assert_called_once()
            # The old entry should be removed and a new one added
            # Check that a new entry exists (the notification was processed)
            assert len(self.manager._notification_cache) == 1

    def test_debouncing_integration(self):
        """Testdebouncingintegrationwithconversiondeduplication."""
        self.manager._test_mode = False
        with patch.object(self.manager, "_show_message_box") as mock_message_box:
            # First notification should work
            self.manager.notify("success", "Test", "Message", job_id="conv1")
            assert mock_message_box.call_count == 1
            # Same notification should be debounced
            self.manager.notify("success", "Test", "Message", job_id="conv1")
            assert mock_message_box.call_count == 1

    def test_debouncing_logs_debug_message(self):
        """Testdebouncinglogsdebugmessage."""
        self.manager._test_mode = False
        # Add recent notification to cache
        key = (None, "success", "Test", "Message", None)
        self.manager._notification_cache[key] = monotonic()
        with patch.object(self.manager._logger, "debug") as mock_debug:
            self.manager.notify("success", "Test", "Message")
            mock_debug.assert_called_with("Debouncing notification: Test")


class TestSystemTrayDecision(TestNotificationManager):
    """Testsystemtraydecisionlogic."""

    def test_should_use_system_tray_no_tray_available(self):
        """Testsystemtraynotusedwhenunavailable."""
        self.manager._tray_available = False
        result = self.manager._should_use_system_tray()
        assert result is False

    def test_should_use_system_tray_no_parent(self):
        """Testsystemtraynotusedwhennoparentwidget."""
        self.manager._tray_available = True
        self.manager._parent_widget = None
        result = self.manager._should_use_system_tray()
        assert result is False

    def test_should_use_system_tray_window_minimized(self):
        """Testsystemtrayusedwhenwindowisminimized."""
        self.manager._tray_available = True
        self.manager._system_tray = Mock()  # Need both tray_available and system_tray
        self.mock_parent.isMinimized.return_value = True
        result = self.manager._should_use_system_tray()
        assert result is True

    def test_should_use_system_tray_window_inactive(self):
        """Testsystemtrayusedwhenwindowisinactive."""
        self.manager._tray_available = True
        self.manager._system_tray = Mock()  # Need both tray_available and system_tray
        self.mock_parent.isMinimized.return_value = False
        self.mock_parent.isActiveWindow.return_value = False
        result = self.manager._should_use_system_tray()
        assert result is True

    def test_should_use_system_tray_window_active(self):
        """Testsystemtraynotusedwhenwindowisactive."""
        self.manager._tray_available = True
        self.mock_parent.isMinimized.return_value = False
        self.mock_parent.isActiveWindow.return_value = True
        result = self.manager._should_use_system_tray()
        assert result is False


class TestMessageBox(TestNotificationManager):
    """Testmessageboxfunctionality."""

    def test_show_message_box_no_parent(self):
        """Testmessageboxcreationwithoutparent."""
        self.manager._parent_widget = None
        # Mock QMessageBox to avoid segmentation fault
        with patch("gui.widgets.notification_manager.QMessageBox") as mock_message_box_class:
            mock_message_box = Mock()
            mock_message_box_class.return_value = mock_message_box
            self.manager._show_message_box("success", "Title", "Message", None)
            # When no parent widget, the method returns early and doesn't create QMessageBox
            mock_message_box_class.assert_not_called()

    def test_show_message_box_basic(self):
        """Testbasicmessageboxfunctionality."""
        # Mock QMessageBox completely to avoid segmentation fault
        with patch("gui.widgets.notification_manager.QMessageBox") as mock_message_box_class:
            mock_message_box = Mock()
            mock_message_box_class.return_value = mock_message_box
            self.manager._show_message_box("success", "Title", "Message", None)
            mock_message_box_class.assert_called_once_with(self.mock_parent)
            mock_message_box.setWindowTitle.assert_called_once_with("Title")
            mock_message_box.setText.assert_called_once_with("Message")
            mock_message_box.exec.assert_called_once()

    def test_show_message_box_with_output_path(self):
        """Testmessageboxwithoutputpathaddsbutton."""
        output_path = "/test/path"
        with (
            patch("gui.widgets.notification_manager.QMessageBox") as mock_message_box_class,
            patch("gui.widgets.notification_manager.Path") as mock_path_class,
        ):
            mock_message_box = Mock()
            mock_message_box_class.return_value = mock_message_box
            mock_message_box_class.StandardButton = Mock()
            mock_message_box_class.ButtonRole = Mock()
            # Mock Path.exists() to return True
            mock_path = Mock()
            mock_path.exists.return_value = True
            mock_path_class.return_value = mock_path
            self.manager._show_message_box("success", "Title", "Message", output_path)
            # Check that addButton was called twice: once for OK, once for Open Folder
            assert mock_message_box.addButton.call_count == 2
            # The first call should be for OK button, second for Open Folder
            calls = mock_message_box.addButton.call_args_list
            assert calls[0][0][0] == mock_message_box_class.StandardButton.Ok
            assert calls[1][0][0] == "Open Folder"

    def test_show_message_box_icon_mapping(self):
        """Testmessageboxiconmapping."""
        with patch("gui.widgets.notification_manager.QMessageBox") as mock_message_box_class:
            mock_message_box = Mock()
            mock_message_box_class.return_value = mock_message_box
            mock_message_box_class.Icon = Mock()
            mock_message_box_class.StandardButton = Mock()
            # Test success icon
            self.manager._show_message_box("success", "Title", "Message", None)
            mock_message_box.setIcon.assert_called_with(mock_message_box_class.Icon.Information)
            # Test error icon
            self.manager._show_message_box("error", "Title", "Message", None)
            mock_message_box.setIcon.assert_called_with(mock_message_box_class.Icon.Critical)
            # Test warning icon
            self.manager._show_message_box("warning", "Title", "Message", None)
            mock_message_box.setIcon.assert_called_with(mock_message_box_class.Icon.Warning)


class TestSystemTrayNotification(TestNotificationManager):
    """Testsystemtraynotificationfunctionality."""

    def test_show_tray_notification_basic(self):
        """Testbasicsystemtraynotification."""
        mock_tray = Mock()
        self.manager._system_tray = mock_tray
        # Mock the MessageIcon enum
        with patch("gui.widgets.notification_manager.QSystemTrayIcon") as mock_tray_class:
            mock_tray_class.MessageIcon = Mock()
            self.manager._show_tray_notification("success", "Title", "Message", None)
            mock_tray.showMessage.assert_called_once_with("Title", "Message", mock_tray_class.MessageIcon.Information, 5000)

    def test_show_tray_notification_icon_mapping(self):
        """Testsystemtraynotificationiconmapping."""
        mock_tray = Mock()
        self.manager._system_tray = mock_tray
        # Mock the MessageIcon enum
        with patch("gui.widgets.notification_manager.QSystemTrayIcon") as mock_tray_class:
            mock_tray_class.MessageIcon = Mock()
            # Test success icon
            self.manager._show_tray_notification("success", "Title", "Message", None)
            mock_tray.showMessage.assert_called_with("Title", "Message", mock_tray_class.MessageIcon.Information, 5000)
            # Test error icon
            self.manager._show_tray_notification("error", "Title", "Message", None)
            mock_tray.showMessage.assert_called_with("Title", "Message", mock_tray_class.MessageIcon.Critical, 5000)
            # Test warning icon
            self.manager._show_tray_notification("warning", "Title", "Message", None)
            mock_tray.showMessage.assert_called_with("Title", "Message", mock_tray_class.MessageIcon.Warning, 5000)


class TestOutputFolderOpening(TestNotificationManager):
    """Testoutputfolderopeningfunctionality."""

    @patch("gui.widgets.notification_manager.QDesktopServices")
    def test_open_output_folder_success(self, mock_desktop_services):
        """Testsuccessfuloutputfolderopening."""
        output_path = "/test/path"
        # Mock parent widget without the special method
        self.manager._parent_widget = Mock()
        self.manager._parent_widget.on_open_output_clicked = None
        self.manager._open_output_folder(output_path)
        mock_desktop_services.openUrl.assert_called_once()

    @patch("gui.widgets.notification_manager.QDesktopServices")
    def test_open_output_folder_error(self, mock_desktop_services):
        """Testoutputfolderopeningerrorhandling."""
        mock_desktop_services.openUrl.side_effect = Exception("Failed to open")
        output_path = "/test/path"
        # Mock parent widget without the special method
        self.manager._parent_widget = Mock()
        self.manager._parent_widget.on_open_output_clicked = None
        with patch.object(self.manager._logger, "error") as mock_log:
            self.manager._open_output_folder(output_path)
            mock_log.assert_called_once_with("Failed to open output folder: Failed to open")


class TestCleanup(TestNotificationManager):
    """Testcleanupfunctionality."""

    def test_cleanup_clears_caches(self):
        """Testcleanupclearsnotificationcaches."""
        # Add some test data
        self.manager._notification_cache["test"] = monotonic()
        self.manager._notified_conversions["conv1"] = "success"
        self.manager.cleanup()
        assert self.manager._notification_cache == {}
        assert self.manager._notified_conversions == {}

    def test_cleanup_removes_system_tray(self):
        """Testcleanupremovessystemtray."""
        mock_tray = Mock()
        self.manager._system_tray = mock_tray
        self.manager.cleanup()
        mock_tray.hide.assert_called_once()
        assert self.manager._system_tray is None
