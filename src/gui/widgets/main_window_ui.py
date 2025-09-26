"""
UI setup and layout management for the main window.

This module provides UI setup functionality for the main window,
separating layout concerns from business logic.
"""

from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from gui.utils.styling import apply_status_style
from gui.widgets.drag_drop import DragDropLabel
from gui.widgets.log_console import LogConsole
from gui.widgets.status_indicator import StatusIndicatorWidget, StatusManager


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

    def setup_ui(self) -> None:
        """Set up the complete user interface."""
        self._setup_window_properties()
        self._setup_central_widget()
        self._setup_keyboard_shortcuts()
        self._setup_accessibility()
        self._load_ui_settings()

    def _setup_window_properties(self) -> None:
        """Set up basic window properties."""
        self.main_window.setWindowTitle("PDF2Foundry GUI")
        self.main_window.setMinimumSize(800, 600)
        self.main_window.resize(1000, 700)

    def _setup_central_widget(self) -> None:
        """Set up the central widget and main layout."""
        self.central_widget = QWidget()
        self.main_window.setCentralWidget(self.central_widget)

        # Main layout
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # File selection area
        self._setup_file_selection_area(main_layout)

        # Status and progress area
        self._setup_status_progress_area(main_layout)

        # Log panel (collapsible)
        self._setup_log_panel(main_layout)

    def _setup_file_selection_area(self, main_layout: QVBoxLayout) -> None:
        """Set up the file selection area."""
        # Drag and drop area
        self.drag_drop_label = DragDropLabel()
        self.drag_drop_label.setMinimumHeight(200)
        main_layout.addWidget(self.drag_drop_label)

        # Browse button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.browse_button = QPushButton("Browse for PDF...")
        self.browse_button.setMinimumHeight(40)
        self.browse_button.setAccessibleName("Browse for PDF file")
        self.browse_button.setAccessibleDescription("Open file dialog to select a PDF file")
        self.browse_button.setToolTip("Browse for PDF file to convert (Ctrl+O)")
        button_layout.addWidget(self.browse_button)

        button_layout.addStretch()
        main_layout.addLayout(button_layout)

    def _setup_status_progress_area(self, main_layout: QVBoxLayout) -> None:
        """Set up the status and progress area."""
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
        self.status_label.setAccessibleDescription("Detailed status message")
        self.status_label.setWhatsThis("Shows detailed status information about the current operation")
        apply_status_style(self.status_label, "default")
        status_layout.addWidget(self.status_label)

        main_layout.addLayout(status_layout)

        # Progress area
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(5)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)  # Hidden initially
        self.progress_bar.setAccessibleName("Conversion progress")
        self.progress_bar.setAccessibleDescription("Shows conversion progress percentage")
        self.progress_bar.setToolTip("Conversion progress")

        # Set fixed height and size policy to prevent layout jitter
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        progress_layout.addWidget(self.progress_bar)

        # Progress status text
        self.progress_status = QLabel()
        self.progress_status.setVisible(False)  # Hidden initially
        self.progress_status.setAccessibleName("Progress status")
        self.progress_status.setAccessibleDescription("Detailed progress status message")

        # Set fixed height and size policy to prevent layout jitter
        self.progress_status.setFixedHeight(16)
        self.progress_status.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        progress_layout.addWidget(self.progress_status)

        main_layout.addLayout(progress_layout)

    def _setup_log_panel(self, main_layout: QVBoxLayout) -> None:
        """Set up the collapsible log panel."""
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
        main_layout.addLayout(log_header_layout)

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

        main_layout.addWidget(self.log_panel)

        # Connect log toggle
        self.log_toggle_button.toggled.connect(self._on_log_toggle)

    def _setup_keyboard_shortcuts(self) -> None:
        """Set up keyboard shortcuts."""
        # Browse shortcut
        browse_action = QAction(self.main_window)
        browse_action.setShortcut(QKeySequence("Ctrl+O"))
        browse_action.triggered.connect(lambda: self.browse_button.clicked.emit() if self.browse_button else None)
        self.main_window.addAction(browse_action)

        # Log panel toggle shortcut
        log_toggle_action = QAction(self.main_window)
        log_toggle_action.setShortcut(QKeySequence("Alt+L"))
        log_toggle_action.triggered.connect(lambda: self.log_toggle_button.toggle() if self.log_toggle_button else None)
        self.main_window.addAction(log_toggle_action)

    def _setup_accessibility(self) -> None:
        """Set up accessibility features."""
        if not (self.drag_drop_label and self.browse_button and self.log_toggle_button):
            return

        # Set up tab order for keyboard navigation
        widgets = [
            self.drag_drop_label,
            self.browse_button,
            self.log_toggle_button,
        ]

        for i in range(len(widgets) - 1):
            self.main_window.setTabOrder(widgets[i], widgets[i + 1])

        # Set initial focus
        self.drag_drop_label.setFocus()

    def _load_ui_settings(self) -> None:
        """Load UI settings from QSettings."""
        settings = QSettings()

        # Load window geometry
        geometry = settings.value("ui/geometry")
        if geometry:
            self.main_window.restoreGeometry(geometry)

        # Load log panel state
        log_expanded = settings.value("ui/logPanelExpanded", True, type=bool)
        if self.log_toggle_button:
            self.log_toggle_button.setChecked(log_expanded)
            self._on_log_toggle(log_expanded)

    def save_ui_settings(self) -> None:
        """Save UI settings to QSettings."""
        settings = QSettings()

        # Save window geometry
        settings.setValue("ui/geometry", self.main_window.saveGeometry())

        # Save log panel state
        if self.log_toggle_button:
            settings.setValue("ui/logPanelExpanded", self.log_toggle_button.isChecked())

    def _on_log_toggle(self, expanded: bool) -> None:
        """Handle log panel toggle."""
        if not (self.log_toggle_button and self.log_panel):
            return

        self.log_panel.setVisible(expanded)
        self.log_toggle_button.setText("▼ Logs" if expanded else "▶ Logs")

        # Save state
        settings = QSettings()
        settings.setValue("ui/logPanelExpanded", expanded)

    def get_default_output_directory(self) -> Path:
        """Get the default output directory."""
        documents_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        if documents_path:
            return Path(documents_path) / "PDF2Foundry Output"
        else:
            return Path.cwd() / "output"
