"""
Layout components and setup for the main window.

This module handles the creation and setup of major layout components,
separating layout logic from the main UI class.
"""

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from gui.widgets.directory_selector import OutputDirectorySelector
from gui.widgets.drag_drop import DragDropLabel


class LayoutComponentsManager:
    """
    Manages layout components for the main window.

    Handles creation and setup of major UI sections and components.
    """

    def __init__(self, main_window: QMainWindow) -> None:
        """
        Initialize the layout components manager.

        Args:
            main_window: The main window to set up components for
        """
        self.main_window = main_window

    def setup_header_bar(self, main_layout: QVBoxLayout) -> QWidget:
        """
        Set up the header bar with app title and action buttons.

        Args:
            main_layout: Main layout to add header to

        Returns:
            Header widget with buttons for external access
        """
        header_widget = QWidget()
        header_widget.setObjectName("headerWidget")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        # App title/branding
        title_label = QLabel("PDF2Foundry GUI")
        title_label.setObjectName("appTitle")
        title_label.setAccessibleName("Application title")
        title_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        header_layout.addWidget(title_label)

        # Spacer to push buttons to the right
        header_layout.addStretch()

        # Help button
        help_button = QToolButton()
        help_button.setObjectName("btnHelp")
        help_button.setText("?")
        help_button.setToolTip("Help and About (F1)")
        help_button.setAccessibleName("Help button")
        help_button.setAccessibleDescription("Show help and about information")
        help_button.setAutoRaise(True)
        help_button.setMinimumSize(32, 32)
        help_button.setStyleSheet("QToolButton { font-weight: bold; font-size: 14px; }")
        header_layout.addWidget(help_button)

        # Settings button
        settings_button = QToolButton()
        settings_button.setObjectName("btnSettings")
        settings_button.setText("⚙")
        settings_button.setToolTip("Settings (Ctrl+,)")
        settings_button.setAccessibleName("Settings button")
        settings_button.setAccessibleDescription("Open application settings")
        settings_button.setAutoRaise(True)
        settings_button.setMinimumSize(32, 32)
        settings_button.setStyleSheet("QToolButton { font-size: 16px; }")
        header_layout.addWidget(settings_button)

        main_layout.addWidget(header_widget)

        # Store references for external access
        header_widget.help_button = help_button  # type: ignore[attr-defined]
        header_widget.settings_button = settings_button  # type: ignore[attr-defined]

        return header_widget

    def setup_output_directory_selector(self, main_layout: QVBoxLayout) -> OutputDirectorySelector:
        """
        Set up the output directory selector row.

        Args:
            main_layout: Layout to add the selector to

        Returns:
            Output directory selector widget
        """
        # Create container widget for the output directory row
        output_dir_widget = QWidget()
        output_dir_widget.setObjectName("outputDirWidget")
        output_dir_layout = QHBoxLayout(output_dir_widget)
        output_dir_layout.setContentsMargins(0, 0, 0, 0)
        output_dir_layout.setSpacing(10)

        # Output directory label
        output_dir_label = QLabel("Output folder:")
        output_dir_label.setObjectName("outputDirLabel")
        output_dir_label.setAccessibleName("Output folder label")
        output_dir_label.setMinimumWidth(100)
        output_dir_layout.addWidget(output_dir_label)

        # Output directory selector widget
        output_dir_selector = OutputDirectorySelector()
        output_dir_selector.setObjectName("outputDirSelector")
        output_dir_selector.setAccessibleName("Output directory selector")
        output_dir_selector.setAccessibleDescription("Select where converted modules will be saved")
        output_dir_layout.addWidget(output_dir_selector, 1)  # Expands to fill space

        main_layout.addWidget(output_dir_widget)
        return output_dir_selector

    def setup_file_selection_area(self, main_layout: QVBoxLayout) -> DragDropLabel:
        """
        Set up the file selection area.

        Args:
            main_layout: Layout to add the file selection to

        Returns:
            Drag and drop label widget
        """
        drag_drop_label = DragDropLabel()
        drag_drop_label.setMinimumHeight(200)
        main_layout.addWidget(drag_drop_label, 3)  # Give it more space
        return drag_drop_label
