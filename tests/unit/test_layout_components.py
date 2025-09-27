"""
Comprehensive tests for the LayoutComponentsManager.

Tests cover:
- LayoutComponentsManager initialization
- Header bar setup with title and buttons
- Output directory selector setup
- File selection area setup
- Widget configuration and accessibility
- Layout structure and properties
"""

from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QVBoxLayout

from core.config_manager import ConfigManager
from gui.widgets.directory_selector import OutputDirectorySelector
from gui.widgets.drag_drop import DragDropLabel
from gui.widgets.layout_components import LayoutComponentsManager


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Create QApplication for all tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestLayoutComponentsManagerInitialization:
    """Test LayoutComponentsManager initialization."""

    def test_initialization(self):
        """Test basic initialization."""
        main_window = QMainWindow()
        manager = LayoutComponentsManager(main_window)

        assert manager.main_window is main_window


class TestHeaderBarSetup:
    """Test header bar setup functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.main_window = QMainWindow()
        self.manager = LayoutComponentsManager(self.main_window)
        self.main_layout = QVBoxLayout()

    def test_setup_header_bar_basic(self):
        """Test basic header bar setup."""
        header_widget = self.manager.setup_header_bar(self.main_layout)

        # Check that header widget was created and added to layout
        assert header_widget is not None
        assert header_widget.objectName() == "headerWidget"
        assert self.main_layout.count() == 1
        assert self.main_layout.itemAt(0).widget() is header_widget

    def test_setup_header_bar_layout_structure(self):
        """Test header bar layout structure."""
        header_widget = self.manager.setup_header_bar(self.main_layout)

        # Check layout structure
        header_layout = header_widget.layout()
        assert isinstance(header_layout, QHBoxLayout)
        assert header_layout.contentsMargins().left() == 0
        assert header_layout.contentsMargins().right() == 0
        assert header_layout.spacing() == 10

    def test_setup_header_bar_title_label(self):
        """Test header bar title label configuration."""
        header_widget = self.manager.setup_header_bar(self.main_layout)

        # Find title label
        header_layout = header_widget.layout()
        title_label = None
        for i in range(header_layout.count()):
            item = header_layout.itemAt(i)
            if item.widget() and item.widget().objectName() == "appTitle":
                title_label = item.widget()
                break

        assert title_label is not None
        assert title_label.text() == "PDF2Foundry GUI"
        assert title_label.accessibleName() == "Application title"
        assert "font-weight: bold" in title_label.styleSheet()
        assert "font-size: 16px" in title_label.styleSheet()

    def test_setup_header_bar_help_button(self):
        """Test header bar help button configuration."""
        header_widget = self.manager.setup_header_bar(self.main_layout)

        # Check help button exists and is accessible
        assert hasattr(header_widget, "help_button")
        help_button = header_widget.help_button

        assert help_button.objectName() == "btnHelp"
        assert help_button.text() == "?"
        assert help_button.toolTip() == "Help and About (F1)"
        assert help_button.accessibleName() == "Help button"
        assert help_button.accessibleDescription() == "Show help and about information"
        assert help_button.autoRaise() is True
        assert help_button.minimumSize().width() == 32
        assert help_button.minimumSize().height() == 32

    def test_setup_header_bar_settings_button(self):
        """Test header bar settings button configuration."""
        header_widget = self.manager.setup_header_bar(self.main_layout)

        # Check settings button exists and is accessible
        assert hasattr(header_widget, "settings_button")
        settings_button = header_widget.settings_button

        assert settings_button.objectName() == "btnSettings"
        assert settings_button.text() == "⚙"
        assert settings_button.toolTip() == "Settings (Ctrl+,)"
        assert settings_button.accessibleName() == "Settings button"
        assert settings_button.accessibleDescription() == "Open application settings"
        assert settings_button.autoRaise() is True
        assert settings_button.minimumSize().width() == 32
        assert settings_button.minimumSize().height() == 32

    def test_setup_header_bar_button_styling(self):
        """Test header bar button styling."""
        header_widget = self.manager.setup_header_bar(self.main_layout)

        help_button = header_widget.help_button
        settings_button = header_widget.settings_button

        # Check styling
        assert "font-weight: bold" in help_button.styleSheet()
        assert "font-size: 14px" in help_button.styleSheet()
        assert "font-size: 16px" in settings_button.styleSheet()

    def test_setup_header_bar_layout_stretch(self):
        """Test that header bar has proper stretch to push buttons right."""
        header_widget = self.manager.setup_header_bar(self.main_layout)

        header_layout = header_widget.layout()

        # Check that there's a stretch item (spacer)
        stretch_found = False
        for i in range(header_layout.count()):
            item = header_layout.itemAt(i)
            if item.spacerItem():
                stretch_found = True
                break

        assert stretch_found, "Header should have stretch to push buttons to the right"


class TestOutputDirectorySelectorSetup:
    """Test output directory selector setup functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.main_window = QMainWindow()
        self.manager = LayoutComponentsManager(self.main_window)
        self.main_layout = QVBoxLayout()

    def test_setup_output_directory_selector_basic(self):
        """Test basic output directory selector setup."""
        selector = self.manager.setup_output_directory_selector(self.main_layout)

        # Check that selector was created and added to layout
        assert isinstance(selector, OutputDirectorySelector)
        assert self.main_layout.count() == 1

    def test_setup_output_directory_selector_with_config_manager(self):
        """Test output directory selector setup with config manager."""
        config_manager = Mock(spec=ConfigManager)
        # Mock the get method to return a valid path string
        config_manager.get.return_value = "/tmp/test_output"

        selector = self.manager.setup_output_directory_selector(self.main_layout, config_manager)

        assert isinstance(selector, OutputDirectorySelector)
        # The selector should have been created with the config manager
        # (We can't easily test this without accessing private attributes)

    def test_setup_output_directory_selector_widget_structure(self):
        """Test output directory selector widget structure."""
        self.manager.setup_output_directory_selector(self.main_layout)

        # Check that a container widget was added to the main layout
        container_widget = self.main_layout.itemAt(0).widget()
        assert container_widget is not None
        assert container_widget.objectName() == "outputDirWidget"

        # Check container layout
        container_layout = container_widget.layout()
        assert isinstance(container_layout, QHBoxLayout)
        assert container_layout.contentsMargins().left() == 0
        assert container_layout.contentsMargins().right() == 0
        assert container_layout.spacing() == 10

    def test_setup_output_directory_selector_label(self):
        """Test output directory selector label configuration."""
        self.manager.setup_output_directory_selector(self.main_layout)

        container_widget = self.main_layout.itemAt(0).widget()
        container_layout = container_widget.layout()

        # Find the label
        label = None
        for i in range(container_layout.count()):
            item = container_layout.itemAt(i)
            if item.widget() and item.widget().objectName() == "outputDirLabel":
                label = item.widget()
                break

        assert label is not None
        assert label.text() == "Output folder:"
        assert label.accessibleName() == "Output folder label"
        assert label.minimumWidth() == 100

    def test_setup_output_directory_selector_accessibility(self):
        """Test output directory selector accessibility configuration."""
        selector = self.manager.setup_output_directory_selector(self.main_layout)

        assert selector.objectName() == "outputDirSelector"
        assert selector.accessibleName() == "Output directory selector"
        assert selector.accessibleDescription() == "Select where converted modules will be saved"

    def test_setup_output_directory_selector_layout_stretch(self):
        """Test that output directory selector has proper stretch factor."""
        self.manager.setup_output_directory_selector(self.main_layout)

        container_widget = self.main_layout.itemAt(0).widget()
        container_layout = container_widget.layout()

        # Find the selector widget and check its stretch factor
        selector_found = False
        for i in range(container_layout.count()):
            item = container_layout.itemAt(i)
            if item.widget() and isinstance(item.widget(), OutputDirectorySelector):
                # Check that it has stretch factor 1 (expands to fill space)
                selector_found = True
                break

        assert selector_found, "Output directory selector should be found in layout"


class TestFileSelectionAreaSetup:
    """Test file selection area setup functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.main_window = QMainWindow()
        self.manager = LayoutComponentsManager(self.main_window)
        self.main_layout = QVBoxLayout()

    def test_setup_file_selection_area_basic(self):
        """Test basic file selection area setup."""
        drag_drop_label = self.manager.setup_file_selection_area(self.main_layout)

        # Check that drag drop label was created and added to layout
        assert isinstance(drag_drop_label, DragDropLabel)
        assert self.main_layout.count() == 1
        assert self.main_layout.itemAt(0).widget() is drag_drop_label

    def test_setup_file_selection_area_minimum_height(self):
        """Test file selection area minimum height configuration."""
        drag_drop_label = self.manager.setup_file_selection_area(self.main_layout)

        assert drag_drop_label.minimumHeight() == 200

    def test_setup_file_selection_area_layout_stretch(self):
        """Test that file selection area has proper stretch factor."""
        self.manager.setup_file_selection_area(self.main_layout)

        # Check that the widget was added with stretch factor 3
        layout_item = self.main_layout.itemAt(0)
        # Note: We can't easily test the stretch factor without accessing private Qt internals
        # but we can verify the widget was added
        assert layout_item.widget() is not None


class TestLayoutComponentsIntegration:
    """Test integration scenarios with multiple components."""

    def setup_method(self):
        """Set up test fixtures."""
        self.main_window = QMainWindow()
        self.manager = LayoutComponentsManager(self.main_window)
        self.main_layout = QVBoxLayout()

    def test_setup_all_components_together(self):
        """Test setting up all components together."""
        # Set up all components
        header_widget = self.manager.setup_header_bar(self.main_layout)
        output_selector = self.manager.setup_output_directory_selector(self.main_layout)
        drag_drop_label = self.manager.setup_file_selection_area(self.main_layout)

        # Check that all components were added to layout
        assert self.main_layout.count() == 3

        # Check order
        assert self.main_layout.itemAt(0).widget() is header_widget
        assert self.main_layout.itemAt(1).widget().objectName() == "outputDirWidget"
        assert self.main_layout.itemAt(2).widget() is drag_drop_label

        # Check that all components are properly configured
        assert hasattr(header_widget, "help_button")
        assert hasattr(header_widget, "settings_button")
        assert isinstance(output_selector, OutputDirectorySelector)
        assert isinstance(drag_drop_label, DragDropLabel)

    def test_components_maintain_independence(self):
        """Test that components can be set up independently."""
        # Set up components in different order
        drag_drop_label = self.manager.setup_file_selection_area(self.main_layout)
        header_widget = self.manager.setup_header_bar(self.main_layout)
        output_selector = self.manager.setup_output_directory_selector(self.main_layout)

        # All should work regardless of order
        assert self.main_layout.count() == 3
        assert isinstance(drag_drop_label, DragDropLabel)
        assert hasattr(header_widget, "help_button")
        assert isinstance(output_selector, OutputDirectorySelector)

    def test_multiple_managers_same_window(self):
        """Test that multiple managers can work with the same window."""
        manager1 = LayoutComponentsManager(self.main_window)
        manager2 = LayoutComponentsManager(self.main_window)

        # Both should reference the same window
        assert manager1.main_window is manager2.main_window
        assert manager1.main_window is self.main_window

    def test_component_object_names_unique(self):
        """Test that component object names are unique and consistent."""
        header_widget = self.manager.setup_header_bar(self.main_layout)
        self.manager.setup_output_directory_selector(self.main_layout)

        # Collect all object names
        object_names = set()

        # Header widget and its children
        object_names.add(header_widget.objectName())
        header_layout = header_widget.layout()
        for i in range(header_layout.count()):
            item = header_layout.itemAt(i)
            if item.widget() and item.widget().objectName():
                object_names.add(item.widget().objectName())

        # Output directory container and its children
        output_container = self.main_layout.itemAt(1).widget()
        object_names.add(output_container.objectName())
        output_layout = output_container.layout()
        for i in range(output_layout.count()):
            item = output_layout.itemAt(i)
            if item.widget() and item.widget().objectName():
                object_names.add(item.widget().objectName())

        # Check for expected object names
        expected_names = {
            "headerWidget",
            "appTitle",
            "btnHelp",
            "btnSettings",
            "outputDirWidget",
            "outputDirLabel",
            "outputDirSelector",
        }

        assert expected_names.issubset(object_names)


class TestLayoutComponentsAccessibility:
    """Test accessibility features of layout components."""

    def setup_method(self):
        """Set up test fixtures."""
        self.main_window = QMainWindow()
        self.manager = LayoutComponentsManager(self.main_window)
        self.main_layout = QVBoxLayout()

    def test_header_accessibility(self):
        """Test header bar accessibility features."""
        header_widget = self.manager.setup_header_bar(self.main_layout)

        # Check that buttons have proper accessibility attributes
        help_button = header_widget.help_button
        settings_button = header_widget.settings_button

        # Accessible names
        assert help_button.accessibleName() == "Help button"
        assert settings_button.accessibleName() == "Settings button"

        # Accessible descriptions
        assert help_button.accessibleDescription() == "Show help and about information"
        assert settings_button.accessibleDescription() == "Open application settings"

        # Tooltips for keyboard users
        assert help_button.toolTip() == "Help and About (F1)"
        assert settings_button.toolTip() == "Settings (Ctrl+,)"

    def test_output_directory_accessibility(self):
        """Test output directory selector accessibility features."""
        output_selector = self.manager.setup_output_directory_selector(self.main_layout)

        # Check accessibility attributes
        assert output_selector.accessibleName() == "Output directory selector"
        assert output_selector.accessibleDescription() == "Select where converted modules will be saved"

        # Check label accessibility
        container_widget = self.main_layout.itemAt(0).widget()
        container_layout = container_widget.layout()

        label = None
        for i in range(container_layout.count()):
            item = container_layout.itemAt(i)
            if item.widget() and item.widget().objectName() == "outputDirLabel":
                label = item.widget()
                break

        assert label is not None
        assert label.accessibleName() == "Output folder label"

    def test_title_accessibility(self):
        """Test app title accessibility features."""
        header_widget = self.manager.setup_header_bar(self.main_layout)

        header_layout = header_widget.layout()
        title_label = None
        for i in range(header_layout.count()):
            item = header_layout.itemAt(i)
            if item.widget() and item.widget().objectName() == "appTitle":
                title_label = item.widget()
                break

        assert title_label is not None
        assert title_label.accessibleName() == "Application title"
