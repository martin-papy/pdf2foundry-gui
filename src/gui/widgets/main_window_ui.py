"""
UI setup and layout management for the main window.

This module provides UI setup functionality for the main window,
separating layout concerns from business logic.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths, Qt
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.config_manager import ConfigManager
from gui.utils.styling import apply_status_style
from gui.widgets.directory_selector import OutputDirectorySelector
from gui.widgets.drag_drop import DragDropLabel
from gui.widgets.keyboard_shortcuts import KeyboardShortcutsManager
from gui.widgets.layout_components import LayoutComponentsManager
from gui.widgets.log_console import LogConsole
from gui.widgets.status_indicator import StatusIndicatorWidget, StatusManager
from gui.widgets.window_properties import WindowPropertiesManager


class MainWindowUI:
    """
    Handles UI setup and layout for the main window.

    Separates UI construction from business logic and event handling.
    """

    def __init__(self, main_window: QMainWindow) -> None:
        """
        Initialize the UI manager.

        Args:
            main_window: The main window to set up
        """
        self.main_window = main_window
        self.central_widget: QWidget | None = None

        # Initialize component managers
        self.window_properties = WindowPropertiesManager(main_window)
        self.layout_components = LayoutComponentsManager(main_window)
        self.keyboard_shortcuts = KeyboardShortcutsManager(main_window)
        self.drag_drop_label: DragDropLabel | None = None
        self.browse_button: QPushButton | None = None
        self.status_label: QLabel | None = None
        self.status_indicator: StatusIndicatorWidget | None = None
        self.status_manager: StatusManager | None = None
        self.progress_bar: QProgressBar | None = None
        self.progress_status: QLabel | None = None
        self.log_toggle_button: QToolButton | None = None
        self.log_console: LogConsole | None = None
        self.log_panel: QFrame | None = None
        self.main_splitter: QSplitter | None = None

        # Header bar components
        self.header_widget: QWidget | None = None
        self.help_button: QToolButton | None = None
        self.settings_button: QToolButton | None = None

        # Output directory selector
        self.output_dir_selector: OutputDirectorySelector | None = None

        # Module configuration fields
        self.module_id_input: QLineEdit | None = None
        self.module_title_input: QLineEdit | None = None

        # Action buttons
        self.convert_button: QPushButton | None = None

        # Custom title bar (optional)
        self.custom_title_bar_enabled: bool = False

    def setup_ui(self, config_manager: ConfigManager | None = None) -> None:
        """Set up the complete user interface."""
        self.window_properties.setup_window_properties()
        self._setup_central_widget(config_manager=config_manager)
        self.keyboard_shortcuts.setup_shortcuts(
            browse_button=self.browse_button,
            help_button=self.help_button,
            settings_button=self.settings_button,
            output_dir_selector=self.output_dir_selector,
            log_toggle_button=self.log_toggle_button,
        )
        self._setup_accessibility()
        self._load_ui_settings()

    def _setup_central_widget(self, config_manager: ConfigManager | None = None) -> None:
        """Set up the central widget and main layout."""
        self.central_widget = QWidget()
        self.main_window.setCentralWidget(self.central_widget)

        # Main layout - contains header and splitter
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Header bar
        self.header_widget = self.layout_components.setup_header_bar(main_layout)
        self.help_button = getattr(self.header_widget, "help_button", None)
        self.settings_button = getattr(self.header_widget, "settings_button", None)

        # Create main splitter (vertical)
        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.main_splitter.setObjectName("mainSplitter")

        # Create main content widget (top part of splitter)
        main_content_widget = QWidget()
        main_content_layout = QVBoxLayout(main_content_widget)
        main_content_layout.setContentsMargins(0, 0, 0, 0)
        main_content_layout.setSpacing(20)

        # Output directory selector
        self.output_dir_selector = self.layout_components.setup_output_directory_selector(
            main_content_layout, config_manager
        )

        # File selection area
        self.drag_drop_label = self.layout_components.setup_file_selection_area(main_content_layout)

        # Button and controls area
        self._setup_button_controls_area(main_content_layout)

        # Status area (without progress - progress will be above logs)
        self._setup_status_area(main_content_layout)

        # Add main content to splitter
        self.main_splitter.addWidget(main_content_widget)

        # Progress area - positioned above logs
        self._setup_progress_area()

        # Log panel (collapsible) - bottom part of splitter
        self._setup_log_panel_with_splitter()

        # Add splitter to main layout
        main_layout.addWidget(self.main_splitter)

    def _setup_button_controls_area(self, main_layout: QVBoxLayout) -> None:
        """Set up the button and controls area (combines browse, module config, convert)."""
        # Create a container widget for all controls
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(15)

        # Button row (browse button)
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.browse_button = QPushButton("Browse…")
        self.browse_button.setMinimumHeight(40)
        self.browse_button.setAccessibleName("Browse for PDF")
        self.browse_button.setAccessibleDescription("Opens a file dialog filtered to PDF files")
        self.browse_button.setToolTip("Choose a PDF file (Ctrl+O)")
        button_layout.addWidget(self.browse_button)

        button_layout.addStretch()
        controls_layout.addLayout(button_layout)

        # Module configuration (conversion controls)
        self._setup_module_config_section(controls_layout)

        # Convert button
        convert_layout = QHBoxLayout()
        convert_layout.addStretch()

        self.convert_button = QPushButton("Convert")
        self.convert_button.setMinimumHeight(50)
        self.convert_button.setMinimumWidth(200)
        self.convert_button.setAccessibleName("Convert PDF")
        self.convert_button.setAccessibleDescription("Start the PDF to Foundry VTT conversion")
        self.convert_button.setToolTip("Start the PDF to Foundry VTT conversion")
        self.convert_button.setEnabled(False)  # Initially disabled until inputs are valid
        convert_layout.addWidget(self.convert_button)

        convert_layout.addStretch()
        controls_layout.addLayout(convert_layout)

        # Add the container to main layout
        main_layout.addWidget(controls_widget)

    def _setup_module_config_section(self, controls_layout: QVBoxLayout) -> None:
        """Set up the module configuration area."""
        # Module configuration group
        module_group = QGroupBox("Module Configuration")
        module_layout = QVBoxLayout(module_group)
        module_layout.setSpacing(10)

        # Module ID input
        id_layout = QHBoxLayout()
        id_label = QLabel("Module ID:")
        id_label.setMinimumWidth(100)
        self.module_id_input = QLineEdit()
        self.module_id_input.setPlaceholderText("e.g., my-awesome-book")
        self.module_id_input.setAccessibleName("Module ID")
        self.module_id_input.setAccessibleDescription("Unique module identifier (lowercase, hyphens only)")
        self.module_id_input.setToolTip(
            "Unique module ID (e.g. 'my-book'). Use lowercase letters, numbers, and hyphens only."
        )

        id_layout.addWidget(id_label)
        id_layout.addWidget(self.module_id_input)
        module_layout.addLayout(id_layout)

        # Module title input
        title_layout = QHBoxLayout()
        title_label = QLabel("Module Title:")
        title_label.setMinimumWidth(100)
        self.module_title_input = QLineEdit()
        self.module_title_input.setPlaceholderText("e.g., My Awesome Book")
        self.module_title_input.setAccessibleName("Module Title")
        self.module_title_input.setAccessibleDescription("Display name shown in Foundry VTT")
        self.module_title_input.setToolTip("Display name shown in Foundry VTT")

        title_layout.addWidget(title_label)
        title_layout.addWidget(self.module_title_input)
        module_layout.addLayout(title_layout)

        controls_layout.addWidget(module_group)

    def _setup_status_area(self, main_layout: QVBoxLayout) -> None:
        """Set up the status area (without progress)."""
        # Status area
        status_layout = QHBoxLayout()
        status_layout.setSpacing(10)

        # Status indicator
        self.status_indicator = StatusIndicatorWidget()
        status_layout.addWidget(self.status_indicator)

        # Status manager
        self.status_manager = StatusManager(self.status_indicator)

        status_layout.addStretch()

        # Status label (for detailed messages)
        self.status_label = QLabel("Ready to convert PDF files")
        self.status_label.setAccessibleName("Status message")
        self.status_label.setAccessibleDescription("Displays the current selection and errors")
        self.status_label.setWhatsThis("Shows detailed status information about the current operation")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        apply_status_style(self.status_label, "default")
        status_layout.addWidget(self.status_label)

        main_layout.addLayout(status_layout)

    def _setup_progress_area(self) -> None:
        """Set up the progress area positioned above logs."""
        if not self.main_splitter:
            return

        # Create progress container widget
        progress_container = QWidget()
        progress_container.setObjectName("progressContainer")
        progress_container_layout = QVBoxLayout(progress_container)
        progress_container_layout.setContentsMargins(0, 5, 0, 5)
        progress_container_layout.setSpacing(5)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setProperty("variant", "primary")  # For QSS theming
        self.progress_bar.setVisible(False)  # Hidden initially
        self.progress_bar.setAccessibleName("Conversion progress")
        self.progress_bar.setAccessibleDescription("Shows conversion progress percentage")
        self.progress_bar.setToolTip("Conversion progress")
        self.progress_bar.setTextVisible(True)  # Show percentage text
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Set fixed height and size policy to prevent layout jitter
        self.progress_bar.setFixedHeight(24)
        self.progress_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        progress_container_layout.addWidget(self.progress_bar)

        # Progress status text
        self.progress_status = QLabel()
        self.progress_status.setObjectName("progressStatus")
        self.progress_status.setVisible(False)  # Hidden initially
        self.progress_status.setAccessibleName("Progress status")
        self.progress_status.setAccessibleDescription("Detailed progress status message")
        self.progress_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_status.setStyleSheet("color: #666; font-size: 12px;")

        # Set fixed height and size policy to prevent layout jitter
        self.progress_status.setFixedHeight(16)
        self.progress_status.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        progress_container_layout.addWidget(self.progress_status)

        # Insert progress container between main content and log container
        # The splitter should have: [main_content, progress_container, log_container]
        if self.main_splitter.count() == 1:
            # Add progress container before setting up log panel
            self.main_splitter.addWidget(progress_container)
            # Set stretch factors: main content can stretch, progress is fixed, logs can stretch
            self.main_splitter.setStretchFactor(0, 1)  # Main content
            self.main_splitter.setStretchFactor(1, 0)  # Progress (fixed)

    def _setup_log_panel_with_splitter(self) -> None:
        """Set up the collapsible log panel using splitter approach."""
        # Create log panel container widget
        log_container = QWidget()
        log_container_layout = QVBoxLayout(log_container)
        log_container_layout.setContentsMargins(0, 0, 0, 0)
        log_container_layout.setSpacing(5)

        # Log panel header
        log_header_layout = QHBoxLayout()
        log_header_layout.setContentsMargins(0, 0, 0, 0)

        self.log_toggle_button = QToolButton()
        self.log_toggle_button.setCheckable(True)
        self.log_toggle_button.setChecked(True)  # Expanded by default
        self.log_toggle_button.setText("▼ Logs")
        self.log_toggle_button.setAccessibleName("Toggle log panel")
        self.log_toggle_button.setAccessibleDescription("Show or hide the log panel")
        self.log_toggle_button.setToolTip("Toggle log panel visibility (Alt+L)")
        log_header_layout.addWidget(self.log_toggle_button)

        log_header_layout.addStretch()
        log_container_layout.addLayout(log_header_layout)

        # Log panel frame
        self.log_panel = QFrame()
        self.log_panel.setObjectName("logPanel")
        self.log_panel.setFrameStyle(QFrame.Shape.StyledPanel)

        log_panel_layout = QVBoxLayout(self.log_panel)
        log_panel_layout.setContentsMargins(5, 5, 5, 5)

        # Log console
        self.log_console = LogConsole(max_entries=10000)
        self.log_console.setMinimumHeight(200)
        self.log_console.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        log_panel_layout.addWidget(self.log_console)

        log_container_layout.addWidget(self.log_panel)

        # Add log container to splitter
        if self.main_splitter:
            self.main_splitter.addWidget(log_container)
            # Set initial splitter sizes: [main_content, progress_container, log_container]
            # Main content gets most space, progress is minimal, logs get reasonable space
            self.main_splitter.setSizes([600, 50, 250])
            self.main_splitter.setStretchFactor(0, 1)  # Main content can stretch
            self.main_splitter.setStretchFactor(1, 0)  # Progress container fixed
            self.main_splitter.setStretchFactor(2, 0)  # Log panel fixed

        # Connect log toggle
        self.log_toggle_button.toggled.connect(self._on_log_toggle_splitter)

    def _setup_accessibility(self) -> None:
        """Set up accessibility features."""
        if not (
            self.drag_drop_label
            and self.browse_button
            and self.module_id_input
            and self.module_title_input
            and self.help_button
            and self.settings_button
            and self.output_dir_selector
            and self.log_toggle_button
        ):
            return

        # Set up tab order for keyboard navigation
        widgets = [
            self.help_button,
            self.settings_button,
            self.output_dir_selector,
            self.drag_drop_label,
            self.browse_button,
            self.module_id_input,
            self.module_title_input,
            self.log_toggle_button,
        ]

        for i in range(len(widgets) - 1):
            self.main_window.setTabOrder(widgets[i], widgets[i + 1])

        # Set initial focus
        self.drag_drop_label.setFocus()

    def _load_ui_settings(self) -> None:
        """Load UI settings from QSettings."""
        settings = QSettings()

        # Load window geometry and state
        geometry = settings.value("ui/geometry")
        if geometry and isinstance(geometry, bytes | bytearray):
            self.main_window.restoreGeometry(geometry)

        # Load window state (for maximize/minimize)
        window_state = settings.value("ui/windowState")
        if window_state and isinstance(window_state, bytes | bytearray):
            self.main_window.restoreState(window_state)

        # Load log panel state (check both old and new settings keys for compatibility)
        logs_collapsed = settings.value("ui/logsCollapsed", False, type=bool)
        log_expanded = not logs_collapsed

        # Fallback to old setting key if new one doesn't exist
        if not settings.contains("ui/logsCollapsed"):
            log_expanded_value = settings.value("ui/logPanelExpanded", True, type=bool)
            log_expanded = bool(log_expanded_value) if log_expanded_value is not None else True

        if self.log_toggle_button and isinstance(log_expanded, bool):
            self.log_toggle_button.setChecked(log_expanded)
            self._on_log_toggle_splitter(log_expanded)

    def save_ui_settings(self) -> None:
        """Save UI settings to QSettings."""
        settings = QSettings()

        # Save window geometry and state
        settings.setValue("ui/geometry", self.main_window.saveGeometry())
        settings.setValue("ui/windowState", self.main_window.saveState())

        # Save log panel state
        if self.log_toggle_button:
            logs_collapsed = not self.log_toggle_button.isChecked()
            settings.setValue("ui/logsCollapsed", logs_collapsed)

            # Also save current splitter sizes if expanded
            if self.main_splitter and self.log_toggle_button.isChecked():
                current_sizes = self.main_splitter.sizes()
                if len(current_sizes) == 3 and current_sizes[2] > 0:
                    settings.setValue("ui/logsSplitter", current_sizes)

    def _on_log_toggle_splitter(self, expanded: bool) -> None:
        """Handle log panel toggle using splitter approach."""
        if not (self.log_toggle_button and self.main_splitter):
            return

        # Update button text
        self.log_toggle_button.setText("▼ Logs" if expanded else "▶ Logs")

        current_sizes = self.main_splitter.sizes()

        if expanded:
            # Restore previous splitter sizes or use defaults
            settings = QSettings()
            saved_sizes = settings.value("ui/logsSplitter", [600, 50, 250])
            if isinstance(saved_sizes, list) and len(saved_sizes) == 3:
                self.main_splitter.setSizes(saved_sizes)
            else:
                # Default: main content, progress, logs
                self.main_splitter.setSizes([600, 50, 250])
        else:
            # Save current sizes before collapsing (only if logs panel is visible)
            if len(current_sizes) == 3 and current_sizes[2] > 0:
                settings = QSettings()
                settings.setValue("ui/logsSplitter", current_sizes)

            # Collapse by setting log panel size to 0, redistribute to main content
            if len(current_sizes) == 3:
                main_size = current_sizes[0] + current_sizes[2]  # Give log space to main content
                progress_size = current_sizes[1]  # Keep progress size
                self.main_splitter.setSizes([main_size, progress_size, 0])

        # Save expanded state
        settings = QSettings()
        settings.setValue("ui/logsCollapsed", not expanded)

    def get_default_output_directory(self) -> Path:
        """Get the default output directory."""
        documents_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        if documents_path:
            return Path(documents_path) / "PDF2Foundry Output"
        else:
            return Path.cwd() / "output"
