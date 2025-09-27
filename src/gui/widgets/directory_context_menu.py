"""
Context menu functionality for the output directory selector widget.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QPoint, Signal
from PySide6.QtWidgets import QMenu, QMessageBox

if TYPE_CHECKING:
    from gui.output.output_folder_controller import OutputFolderController
    from gui.widgets.directory_selector import OutputDirectorySelector


class DirectoryContextMenu(QObject):
    """Handles context menu functionality for directory operations."""

    # Signals
    last_export_requested = Signal()

    def __init__(self, parent_widget: "OutputDirectorySelector", controller: "OutputFolderController") -> None:
        super().__init__(parent_widget)
        self.parent_widget = parent_widget
        self.controller = controller
        self._setup_context_menu()

    def _setup_context_menu(self) -> None:
        """Set up the context menu for the path input field."""
        if hasattr(self.parent_widget, "path_edit") and self.parent_widget.path_edit:
            from PySide6.QtCore import Qt

            self.parent_widget.path_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.parent_widget.path_edit.customContextMenuRequested.connect(self._show_context_menu)

    def _show_context_menu(self, position: QPoint) -> None:
        """Show context menu at the given position."""
        if not hasattr(self.parent_widget, "path_edit") or not self.parent_widget.path_edit:
            return

        menu = QMenu(self.parent_widget)

        # Add standard context menu actions
        if self.parent_widget.path_edit.hasSelectedText():
            menu.addAction("Cut", self.parent_widget.path_edit.cut)
            menu.addAction("Copy", self.parent_widget.path_edit.copy)

        # Check if clipboard has text content
        from PySide6.QtGui import QGuiApplication

        clipboard = QGuiApplication.clipboard()
        if clipboard and clipboard.text():
            menu.addAction("Paste", self.parent_widget.path_edit.paste)

        menu.addSeparator()

        # Add custom actions
        last_export_path = self.controller.last_export_path()
        if last_export_path and last_export_path.exists():
            menu.addAction("Open Last Export Location", self._on_open_last_export_clicked)

        # Show the menu
        global_pos = self.parent_widget.path_edit.mapToGlobal(position)
        menu.exec(global_pos)

    def _on_open_last_export_clicked(self) -> None:
        """Handle opening the last export location."""
        last_export_path = self.controller.last_export_path()
        if not last_export_path or not last_export_path.exists():
            QMessageBox.information(
                self.parent_widget,
                "No Export Location",
                "No previous export location found or the location no longer exists.",
            )
            return

        # Import here to avoid circular imports
        from gui.utils.fs import open_in_file_manager

        success = open_in_file_manager(last_export_path)
        if not success:
            QMessageBox.warning(
                self.parent_widget, "Cannot Open Location", f"Failed to open the export location:\n{last_export_path}"
            )

    def set_last_export_path(self, path: Path) -> None:
        """Set the last export path in the controller."""
        self.controller.set_last_export_path(path)
