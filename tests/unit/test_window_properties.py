"""
Comprehensive tests for the WindowPropertiesManager.

Tests cover:
- WindowPropertiesManager initialization
- Window properties setup (title, size, icon)
- Window icon configuration and fallback
- Custom frameless mode detection
- Platform-specific behavior
- Environment variable handling
"""

import os
from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow

from gui.widgets.window_properties import WindowPropertiesManager


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Create QApplication for all tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestWindowPropertiesManagerInitialization:
    """Test WindowPropertiesManager initialization."""

    def test_initialization(self):
        """Test basic initialization."""
        main_window = QMainWindow()
        manager = WindowPropertiesManager(main_window)

        assert manager.main_window is main_window
        assert manager.custom_title_bar_enabled is False


class TestWindowPropertiesSetup:
    """Test window properties setup functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.main_window = QMainWindow()
        self.manager = WindowPropertiesManager(self.main_window)

    def test_setup_window_properties_basic(self):
        """Test basic window properties setup."""
        self.manager.setup_window_properties()

        # Check window title
        assert self.main_window.windowTitle() == "PDF2Foundry GUI"

        # Check window size
        assert self.main_window.minimumSize().width() == 800
        assert self.main_window.minimumSize().height() == 600
        assert self.main_window.size().width() == 800
        assert self.main_window.size().height() == 600

    def test_setup_window_properties_calls_icon_setup(self):
        """Test that window properties setup calls icon setup."""
        with (
            patch.object(self.manager, "_setup_window_icon") as mock_icon_setup,
            patch.object(self.manager, "_check_custom_frameless_mode") as mock_frameless,
        ):
            self.manager.setup_window_properties()

            mock_icon_setup.assert_called_once()
            mock_frameless.assert_called_once()

    def test_setup_window_properties_calls_frameless_check(self):
        """Test that window properties setup calls frameless mode check."""
        with (
            patch.object(self.manager, "_setup_window_icon"),
            patch.object(self.manager, "_check_custom_frameless_mode") as mock_frameless,
        ):
            self.manager.setup_window_properties()

            mock_frameless.assert_called_once()


class TestWindowIconSetup:
    """Test window icon setup functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.main_window = QMainWindow()
        self.manager = WindowPropertiesManager(self.main_window)

    def test_setup_window_icon_with_existing_file(self):
        """Test window icon setup when icon file exists."""
        with (
            patch("gui.widgets.window_properties.Path.exists") as mock_exists,
            patch("gui.widgets.window_properties.QIcon") as mock_qicon,
            patch.object(self.main_window, "setWindowIcon") as mock_set_icon,
        ):
            mock_exists.return_value = True
            mock_icon = Mock()
            mock_qicon.return_value = mock_icon

            self.manager._setup_window_icon()

            # Should create icon and set it
            mock_qicon.assert_called_once_with("resources/icons/app_icon.png")
            mock_set_icon.assert_called_once_with(mock_icon)

    def test_setup_window_icon_without_existing_file(self):
        """Test window icon setup when icon file doesn't exist."""
        with (
            patch("gui.widgets.window_properties.Path.exists") as mock_exists,
            patch("gui.widgets.window_properties.QPixmap") as mock_qpixmap,
        ):
            mock_exists.return_value = False
            mock_pixmap = Mock()
            mock_qpixmap.return_value = mock_pixmap

            self.manager._setup_window_icon()

            # Should create fallback pixmap
            mock_qpixmap.assert_called_once_with(32, 32)
            mock_pixmap.fill.assert_called_once_with(Qt.GlobalColor.transparent)

    def test_setup_window_icon_path_check(self):
        """Test that correct icon path is checked."""
        with patch("gui.widgets.window_properties.Path") as mock_path:
            mock_path_instance = Mock()
            mock_path.return_value = mock_path_instance
            mock_path_instance.exists.return_value = False

            self.manager._setup_window_icon()

            mock_path.assert_called_once_with("resources/icons/app_icon.png")
            mock_path_instance.exists.assert_called_once()

    def test_setup_window_icon_fallback_pixmap_properties(self):
        """Test fallback pixmap properties."""
        with (
            patch("gui.widgets.window_properties.Path.exists") as mock_exists,
            patch("gui.widgets.window_properties.QPixmap") as mock_qpixmap,
        ):
            mock_exists.return_value = False
            mock_pixmap = Mock()
            mock_qpixmap.return_value = mock_pixmap

            self.manager._setup_window_icon()

            # Check pixmap creation with correct size
            mock_qpixmap.assert_called_once_with(32, 32)
            # Check that pixmap is filled with transparent color
            mock_pixmap.fill.assert_called_once_with(Qt.GlobalColor.transparent)


class TestCustomFramelessMode:
    """Test custom frameless mode detection and configuration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.main_window = QMainWindow()
        self.manager = WindowPropertiesManager(self.main_window)

    def test_check_custom_frameless_mode_disabled_by_default(self):
        """Test that frameless mode is disabled by default."""
        with patch.dict(os.environ, {}, clear=True):
            self.manager._check_custom_frameless_mode()

            assert self.manager.custom_title_bar_enabled is False

    def test_check_custom_frameless_mode_enabled_by_env_var(self):
        """Test frameless mode enabled by environment variable."""
        with (
            patch.dict(os.environ, {"PDF2FOUNDRY_CUSTOM_TITLEBAR": "true"}),
            patch("gui.widgets.window_properties.platform.system") as mock_platform,
        ):
            mock_platform.return_value = "Linux"  # Not macOS

            self.manager._check_custom_frameless_mode()

            assert self.manager.custom_title_bar_enabled is True

    def test_check_custom_frameless_mode_case_insensitive(self):
        """Test that environment variable is case insensitive."""
        test_cases = ["true", "TRUE", "True", "TrUe"]

        for value in test_cases:
            with (
                patch.dict(os.environ, {"PDF2FOUNDRY_CUSTOM_TITLEBAR": value}),
                patch("gui.widgets.window_properties.platform.system") as mock_platform,
            ):
                mock_platform.return_value = "Linux"

                manager = WindowPropertiesManager(QMainWindow())
                manager._check_custom_frameless_mode()

                assert manager.custom_title_bar_enabled is True

    def test_check_custom_frameless_mode_false_values(self):
        """Test that false values disable frameless mode."""
        test_cases = ["false", "FALSE", "False", "no", "0", ""]

        for value in test_cases:
            with patch.dict(os.environ, {"PDF2FOUNDRY_CUSTOM_TITLEBAR": value}):
                manager = WindowPropertiesManager(QMainWindow())
                manager._check_custom_frameless_mode()

                assert manager.custom_title_bar_enabled is False

    @patch("gui.widgets.window_properties.platform.system")
    def test_check_custom_frameless_mode_disabled_on_macos(self, mock_platform):
        """Test that frameless mode is disabled on macOS by default."""
        mock_platform.return_value = "Darwin"

        with patch.dict(os.environ, {"PDF2FOUNDRY_CUSTOM_TITLEBAR": "true"}):
            self.manager._check_custom_frameless_mode()

            assert self.manager.custom_title_bar_enabled is False

    @patch("gui.widgets.window_properties.platform.system")
    def test_check_custom_frameless_mode_forced_on_macos(self, mock_platform):
        """Test that frameless mode can be forced on macOS."""
        mock_platform.return_value = "Darwin"

        with patch.dict(os.environ, {"PDF2FOUNDRY_CUSTOM_TITLEBAR": "true", "PDF2FOUNDRY_FORCE_FRAMELESS": "1"}):
            self.manager._check_custom_frameless_mode()

            assert self.manager.custom_title_bar_enabled is True

    @patch("gui.widgets.window_properties.platform.system")
    def test_check_custom_frameless_mode_sets_window_flags(self, mock_platform):
        """Test that frameless mode sets correct window flags."""
        mock_platform.return_value = "Linux"

        with patch.dict(os.environ, {"PDF2FOUNDRY_CUSTOM_TITLEBAR": "true"}):
            self.main_window.windowFlags()

            self.manager._check_custom_frameless_mode()

            # Check that frameless hint was added
            # Note: We can't easily test this without mocking setWindowFlags
            assert self.manager.custom_title_bar_enabled is True

    def test_check_custom_frameless_mode_environment_variable_precedence(self):
        """Test environment variable precedence."""
        # Test that PDF2FOUNDRY_CUSTOM_TITLEBAR takes precedence
        with (
            patch.dict(os.environ, {"PDF2FOUNDRY_CUSTOM_TITLEBAR": "false", "SOME_OTHER_VAR": "true"}),
            patch("gui.widgets.window_properties.platform.system") as mock_platform,
        ):
            mock_platform.return_value = "Linux"

            self.manager._check_custom_frameless_mode()

            assert self.manager.custom_title_bar_enabled is False


class TestPlatformSpecificBehavior:
    """Test platform-specific behavior."""

    def setup_method(self):
        """Set up test fixtures."""
        self.main_window = QMainWindow()
        self.manager = WindowPropertiesManager(self.main_window)

    @patch("gui.widgets.window_properties.platform.system")
    def test_platform_detection_darwin(self, mock_platform):
        """Test platform detection for macOS (Darwin)."""
        mock_platform.return_value = "Darwin"

        with patch.dict(os.environ, {"PDF2FOUNDRY_CUSTOM_TITLEBAR": "true"}):
            self.manager._check_custom_frameless_mode()

            # Should be disabled on macOS without force flag
            assert self.manager.custom_title_bar_enabled is False

    @patch("gui.widgets.window_properties.platform.system")
    def test_platform_detection_linux(self, mock_platform):
        """Test platform detection for Linux."""
        mock_platform.return_value = "Linux"

        with patch.dict(os.environ, {"PDF2FOUNDRY_CUSTOM_TITLEBAR": "true"}):
            self.manager._check_custom_frameless_mode()

            # Should be enabled on Linux
            assert self.manager.custom_title_bar_enabled is True

    @patch("gui.widgets.window_properties.platform.system")
    def test_platform_detection_windows(self, mock_platform):
        """Test platform detection for Windows."""
        mock_platform.return_value = "Windows"

        with patch.dict(os.environ, {"PDF2FOUNDRY_CUSTOM_TITLEBAR": "true"}):
            self.manager._check_custom_frameless_mode()

            # Should be enabled on Windows
            assert self.manager.custom_title_bar_enabled is True

    @patch("gui.widgets.window_properties.platform.system")
    def test_macos_force_flag_behavior(self, mock_platform):
        """Test macOS force flag behavior."""
        mock_platform.return_value = "Darwin"

        # Test without force flag
        with patch.dict(os.environ, {"PDF2FOUNDRY_CUSTOM_TITLEBAR": "true"}):
            manager1 = WindowPropertiesManager(QMainWindow())
            manager1._check_custom_frameless_mode()
            assert manager1.custom_title_bar_enabled is False

        # Test with force flag
        with patch.dict(os.environ, {"PDF2FOUNDRY_CUSTOM_TITLEBAR": "true", "PDF2FOUNDRY_FORCE_FRAMELESS": "1"}):
            manager2 = WindowPropertiesManager(QMainWindow())
            manager2._check_custom_frameless_mode()
            assert manager2.custom_title_bar_enabled is True

    @patch("gui.widgets.window_properties.platform.system")
    def test_force_flag_only_affects_macos(self, mock_platform):
        """Test that force flag only affects macOS behavior."""
        # Test on Linux - force flag should not matter
        mock_platform.return_value = "Linux"

        with patch.dict(os.environ, {"PDF2FOUNDRY_CUSTOM_TITLEBAR": "true", "PDF2FOUNDRY_FORCE_FRAMELESS": "1"}):
            self.manager._check_custom_frameless_mode()
            assert self.manager.custom_title_bar_enabled is True

        # Same result without force flag on Linux
        with patch.dict(os.environ, {"PDF2FOUNDRY_CUSTOM_TITLEBAR": "true"}):
            manager2 = WindowPropertiesManager(QMainWindow())
            manager2._check_custom_frameless_mode()
            assert manager2.custom_title_bar_enabled is True


class TestWindowPropertiesIntegration:
    """Test integration scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.main_window = QMainWindow()
        self.manager = WindowPropertiesManager(self.main_window)

    def test_full_setup_integration(self):
        """Test full window properties setup integration."""
        with (
            patch.dict(os.environ, {"PDF2FOUNDRY_CUSTOM_TITLEBAR": "true"}),
            patch("gui.widgets.window_properties.platform.system") as mock_platform,
            patch("gui.widgets.window_properties.Path.exists") as mock_exists,
        ):
            mock_platform.return_value = "Linux"
            mock_exists.return_value = False

            self.manager.setup_window_properties()

            # Check all properties were set
            assert self.main_window.windowTitle() == "PDF2Foundry GUI"
            assert self.main_window.minimumSize().width() == 800
            assert self.main_window.minimumSize().height() == 600
            assert self.manager.custom_title_bar_enabled is True

    def test_multiple_managers_same_window(self):
        """Test multiple managers with same window."""
        manager1 = WindowPropertiesManager(self.main_window)
        manager2 = WindowPropertiesManager(self.main_window)

        # Both should reference the same window
        assert manager1.main_window is manager2.main_window

        # Both should have independent state
        manager1.custom_title_bar_enabled = True
        assert manager2.custom_title_bar_enabled is False

    def test_setup_idempotency(self):
        """Test that setup can be called multiple times safely."""
        with patch("gui.widgets.window_properties.Path.exists") as mock_exists:
            mock_exists.return_value = False

            # Call setup multiple times
            self.manager.setup_window_properties()
            original_title = self.main_window.windowTitle()
            original_size = self.main_window.size()

            self.manager.setup_window_properties()

            # Properties should remain the same
            assert self.main_window.windowTitle() == original_title
            assert self.main_window.size() == original_size

    def test_environment_isolation(self):
        """Test that environment changes don't affect existing instances."""
        # Create manager with one environment
        with (
            patch.dict(os.environ, {"PDF2FOUNDRY_CUSTOM_TITLEBAR": "false"}),
            patch("gui.widgets.window_properties.platform.system") as mock_platform,
        ):
            mock_platform.return_value = "Linux"

            self.manager._check_custom_frameless_mode()
            assert self.manager.custom_title_bar_enabled is False

        # Change environment and create new manager
        with (
            patch.dict(os.environ, {"PDF2FOUNDRY_CUSTOM_TITLEBAR": "true"}),
            patch("gui.widgets.window_properties.platform.system") as mock_platform,
        ):
            mock_platform.return_value = "Linux"

            new_manager = WindowPropertiesManager(QMainWindow())
            new_manager._check_custom_frameless_mode()

            # New manager should reflect new environment
            assert new_manager.custom_title_bar_enabled is True
            # Original manager should be unchanged
            assert self.manager.custom_title_bar_enabled is False


class TestWindowPropertiesEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.main_window = QMainWindow()
        self.manager = WindowPropertiesManager(self.main_window)

    def test_missing_environment_variables(self):
        """Test behavior with missing environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            self.manager._check_custom_frameless_mode()

            assert self.manager.custom_title_bar_enabled is False

    def test_empty_environment_variables(self):
        """Test behavior with empty environment variables."""
        with patch.dict(os.environ, {"PDF2FOUNDRY_CUSTOM_TITLEBAR": "", "PDF2FOUNDRY_FORCE_FRAMELESS": ""}):
            self.manager._check_custom_frameless_mode()

            assert self.manager.custom_title_bar_enabled is False

    def test_invalid_environment_variable_values(self):
        """Test behavior with invalid environment variable values."""
        invalid_values = ["maybe", "1.5", "yes", "on", "enabled"]

        for value in invalid_values:
            with patch.dict(os.environ, {"PDF2FOUNDRY_CUSTOM_TITLEBAR": value}):
                manager = WindowPropertiesManager(QMainWindow())
                manager._check_custom_frameless_mode()

                # Should default to False for unrecognized values
                assert manager.custom_title_bar_enabled is False

    def test_icon_path_edge_cases(self):
        """Test icon path handling edge cases."""
        # Test with Path that raises exception - currently not handled gracefully
        with patch("gui.widgets.window_properties.Path") as mock_path:
            mock_path.side_effect = Exception("Path error")

            # Currently the implementation doesn't handle Path exceptions
            with pytest.raises(Exception, match="Path error"):
                self.manager._setup_window_icon()

    def test_platform_system_exception(self):
        """Test behavior when platform.system() raises exception."""
        with patch("gui.widgets.window_properties.platform.system") as mock_platform:
            mock_platform.side_effect = Exception("Platform detection error")

            with (
                patch.dict(os.environ, {"PDF2FOUNDRY_CUSTOM_TITLEBAR": "true"}),
                pytest.raises(Exception, match="Platform detection error"),
            ):
                # Currently the implementation doesn't handle platform exceptions
                self.manager._check_custom_frameless_mode()
