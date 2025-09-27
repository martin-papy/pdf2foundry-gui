"""
Main window UI setup for the PDF2Foundry GUI.

This module contains the MainWindowUI class which sets up the user interface
components for the main application window.
"""

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.config_manager import ConfigManager
from gui.widgets.directory_selector import OutputDirectorySelector
from gui.widgets.drag_drop import DragDropLabel
from gui.widgets.keyboard_shortcuts import KeyboardShortcutsManager
from gui.widgets.log_console import LogConsole
from gui.widgets.status_indicator import StatusIndicatorWidget
from gui.widgets.ui_components.button_setup import ButtonSetup
from gui.widgets.ui_components.module_config_setup import ModuleConfigSetup
from gui.widgets.ui_components.settings_manager import UISettingsManager


class MainWindowUI(QWidget):
    """
    Main window UI setup and management.

    This class handles the creation and layout of all UI components
    for the main application window.
    """

    def __init__(self, main_window: QMainWindow) -> None:
        """Initialize the main window UI."""
        super().__init__()
        self.main_window = main_window
        self._logger = logging.getLogger(__name__)

        # Initialize UI component managers
        self.button_setup = ButtonSetup(self)
        self.module_config_setup = ModuleConfigSetup(self)
        self.settings_manager = UISettingsManager(self)

        # UI component references
        self.drag_drop_label: DragDropLabel | None = None
        self.browse_button: QPushButton | None = None
        self.convert_button: QPushButton | None = None
        self.cancel_button: QPushButton | None = None
        self.open_output_button: QToolButton | None = None
        self.module_id_input: QLineEdit | None = None
        self.module_title_input: QLineEdit | None = None
        self.output_dir_selector: OutputDirectorySelector | None = None
        self.status_indicator_widget: StatusIndicatorWidget | None = None
        self.progress_bar: QProgressBar | None = None
        self.progress_status: QLabel | None = None
        self.log_console: LogConsole | None = None
        self.main_splitter: QSplitter | None = None
        self.settings_button: QPushButton | None = None
        self.help_button: QPushButton | None = None
        self.status_label: QLabel | None = None

        # Set up the UI
        self.setup_ui()

    def setup_ui(self, config_manager: ConfigManager | None = None) -> None:
        """Set up the main UI components."""
        # Set window properties
        self.main_window.setWindowTitle("PDF2Foundry GUI")
        self.main_window.setMinimumSize(800, 600)
        self.main_window.resize(800, 600)

        # Set up the central widget
        self._setup_central_widget(config_manager)

        # Set up accessibility
        self._setup_accessibility()

        # Load UI settings
        self.settings_manager.load_ui_settings()

    def _setup_central_widget(self, config_manager: ConfigManager | None = None) -> None:
        """Set up the central widget with main layout."""
        # Create main layout with expected margins and spacing
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Create header widget (contains drag-drop, buttons, inputs, status)
        self.header_widget = QWidget()
        header_layout = QVBoxLayout(self.header_widget)
        header_layout.setSpacing(16)
        header_layout.setContentsMargins(0, 0, 0, 0)

        # Create and set up drag and drop area
        self.drag_drop_label = DragDropLabel()
        self.drag_drop_label.setMinimumHeight(120)
        header_layout.addWidget(self.drag_drop_label)

        # Set up button controls
        self.button_setup.setup_button_controls_area(header_layout)

        # Create controls layout for inputs
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(12)

        # Set up module configuration section
        self.module_config_setup.setup_module_config_section(controls_layout)

        # Set up output directory selector
        self.output_dir_selector = OutputDirectorySelector(parent=self, config_manager=config_manager)
        controls_layout.addWidget(self.output_dir_selector)

        header_layout.addLayout(controls_layout)

        # Set up status area
        self._setup_status_area(header_layout)

        # Set up progress area
        self._setup_progress_area()

        # Add header widget to main layout
        main_layout.addWidget(self.header_widget)

        # Set up log panel with splitter
        self._setup_log_panel_with_splitter(main_layout)

    def _setup_status_area(self, main_layout: QVBoxLayout) -> None:
        """Set up the status indicator area."""
        # Create status layout
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 8, 0, 8)

        # Create status indicator widget
        self.status_indicator_widget = StatusIndicatorWidget()
        status_layout.addWidget(self.status_indicator_widget)

        # Create status label for backward compatibility
        self.status_label = QLabel("Ready to convert PDF files")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAccessibleName("Status message")
        self.status_label.setAccessibleDescription("Displays the current selection and errors")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(self.status_label)

        # Add stretch to push status to the left
        status_layout.addStretch()

        # Add buttons area (settings, help, etc.)
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)

        # Settings button
        self.settings_button = QPushButton("Settings")
        self.settings_button.setObjectName("settingsButton")
        buttons_layout.addWidget(self.settings_button)

        # Help button
        self.help_button = QPushButton("Help")
        self.help_button.setObjectName("helpButton")
        buttons_layout.addWidget(self.help_button)

        status_layout.addLayout(buttons_layout)
        main_layout.addLayout(status_layout)

    def _setup_progress_area(self) -> None:
        """Set up the progress bar and status area."""
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setMinimumHeight(24)
        self.progress_bar.setVisible(False)  # Initially hidden
        self.progress_bar.setAccessibleName("Conversion progress")
        self.progress_bar.setAccessibleDescription("Shows the current progress of the PDF conversion")

        # Progress status label
        self.progress_status = QLabel()
        self.progress_status.setObjectName("progressStatus")
        self.progress_status.setVisible(False)  # Initially hidden
        self.progress_status.setAccessibleName("Progress status")
        self.progress_status.setAccessibleDescription("Shows detailed status of the conversion process")

        # Note: These will be added to the layout by the splitter setup

    def _setup_log_panel_with_splitter(self, main_layout: QVBoxLayout) -> None:
        """Set up the log panel with a splitter for resizing."""
        # Create main splitter
        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.main_splitter.setObjectName("mainSplitter")

        # Add progress area to header widget if not already added
        if self.progress_bar and self.progress_bar.parent() is None:
            self.header_widget.layout().addWidget(self.progress_bar)
        if self.progress_status and self.progress_status.parent() is None:
            self.header_widget.layout().addWidget(self.progress_status)

        # Create log console
        self.log_console = LogConsole()
        self.log_console.setMinimumHeight(150)

        # Add widgets to splitter
        # Note: header_widget is already added to main_layout, so we don't add it to splitter
        self.main_splitter.addWidget(self.log_console)

        # Add splitter to main layout
        main_layout.addWidget(self.main_splitter)

        # Set initial splitter sizes (70% main content, 30% log panel)
        self.main_splitter.setSizes([400, 200])

        # Set splitter properties - only set collapsible for widgets that exist
        if self.main_splitter.count() > 0:
            self.main_splitter.setCollapsible(0, False)  # Don't allow main content to collapse
        if self.main_splitter.count() > 1:
            self.main_splitter.setCollapsible(1, True)  # Allow log panel to collapse

    def _setup_accessibility(self) -> None:
        """Set up accessibility properties and tab order."""
        # Set up keyboard shortcuts
        shortcuts_manager = KeyboardShortcutsManager(self.main_window)
        shortcuts_manager.setup_shortcuts(
            browse_button=self.browse_button,
            output_dir_selector=self.output_dir_selector,
            convert_button=self.convert_button,
            cancel_button=self.cancel_button,
            open_output_button=self.open_output_button,
            settings_button=self.settings_button,
            help_button=self.help_button,
        )

        # Set tab order for keyboard navigation
        tab_widgets: list[QWidget] = []
        if self.drag_drop_label:
            tab_widgets.append(self.drag_drop_label)
        if self.browse_button:
            tab_widgets.append(self.browse_button)
        if self.module_id_input:
            tab_widgets.append(self.module_id_input)
        if self.module_title_input:
            tab_widgets.append(self.module_title_input)
        if self.output_dir_selector:
            tab_widgets.append(self.output_dir_selector)
        if self.convert_button:
            tab_widgets.append(self.convert_button)
        if self.cancel_button:
            tab_widgets.append(self.cancel_button)
        if self.open_output_button:
            tab_widgets.append(self.open_output_button)
        if self.settings_button:
            tab_widgets.append(self.settings_button)
        if self.help_button:
            tab_widgets.append(self.help_button)

        # Set tab order
        for i in range(len(tab_widgets) - 1):
            self.main_window.setTabOrder(tab_widgets[i], tab_widgets[i + 1])

    def save_ui_settings(self) -> None:
        """Save UI settings."""
        self.settings_manager.save_ui_settings()

    def get_default_output_directory(self) -> Path:
        """Get the default output directory."""
        return self.settings_manager.get_default_output_directory()
