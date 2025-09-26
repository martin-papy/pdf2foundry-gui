"""
UI controls for the LogConsole widget.

This module provides the filter and search controls for the log console.
"""

from PySide6.QtCore import QSettings, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from gui.utils.styling import AccessiblePalette


class LogControlsWidget(QWidget):
    """
    Widget containing filter and search controls for the log console.

    Provides level filtering, text search, auto-scroll toggle, and navigation controls.
    """

    # Signals
    levelFilterChanged = Signal(str)  # Emitted when level filter changes
    searchTextChanged = Signal(str)  # Emitted when search text changes
    searchCleared = Signal()  # Emitted when search is cleared
    nextMatchRequested = Signal()  # Emitted when next match is requested
    previousMatchRequested = Signal()  # Emitted when previous match is requested
    autoScrollToggled = Signal(bool)  # Emitted when auto-scroll is toggled
    jumpToEndRequested = Signal()  # Emitted when jump to end is requested

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the log controls widget."""
        super().__init__(parent)
        self._setup_ui()
        self._setup_keyboard_shortcuts()
        self._load_settings()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Level filter
        filter_label = QLabel("Filter:")
        filter_label.setAccessibleName("Log level filter label")
        layout.addWidget(filter_label)

        self._level_filter = QComboBox()
        self._level_filter.addItems(["All", "INFO", "WARNING", "ERROR"])
        self._level_filter.setAccessibleName("Log level filter")
        self._level_filter.setAccessibleDescription("Filter log messages by level")
        self._level_filter.setToolTip("Filter log messages by level")
        self._level_filter.currentTextChanged.connect(self._on_level_filter_changed)
        layout.addWidget(self._level_filter)

        layout.addSpacing(16)

        # Search
        search_label = QLabel("Search:")
        search_label.setAccessibleName("Search label")
        layout.addWidget(search_label)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search logs...")
        self._search_input.setAccessibleName("Search input")
        self._search_input.setAccessibleDescription("Search for text in log messages")
        self._search_input.setToolTip("Search for text in log messages (case-insensitive)")
        self._search_input.textChanged.connect(self.searchTextChanged.emit)
        layout.addWidget(self._search_input)

        # Clear search button
        self._clear_search_btn = QPushButton("✕")
        self._clear_search_btn.setFixedSize(24, 24)
        self._clear_search_btn.setAccessibleName("Clear search")
        self._clear_search_btn.setAccessibleDescription("Clear the current search")
        self._clear_search_btn.setToolTip("Clear search (Escape)")
        self._clear_search_btn.clicked.connect(self._on_clear_search)
        layout.addWidget(self._clear_search_btn)

        # Search navigation
        self._prev_match_btn = QPushButton("↑")
        self._prev_match_btn.setFixedSize(24, 24)
        self._prev_match_btn.setAccessibleName("Previous match")
        self._prev_match_btn.setAccessibleDescription("Go to previous search match")
        self._prev_match_btn.setToolTip("Previous match (Shift+F3)")
        self._prev_match_btn.clicked.connect(self.previousMatchRequested.emit)
        layout.addWidget(self._prev_match_btn)

        self._next_match_btn = QPushButton("↓")
        self._next_match_btn.setFixedSize(24, 24)
        self._next_match_btn.setAccessibleName("Next match")
        self._next_match_btn.setAccessibleDescription("Go to next search match")
        self._next_match_btn.setToolTip("Next match (F3)")
        self._next_match_btn.clicked.connect(self.nextMatchRequested.emit)
        layout.addWidget(self._next_match_btn)

        # Match counter
        self._match_counter = QLabel()
        self._match_counter.setAccessibleName("Match counter")
        self._match_counter.setMinimumWidth(80)
        layout.addWidget(self._match_counter)

        layout.addStretch()

        # Auto-scroll controls
        self._auto_scroll_checkbox = QCheckBox("Auto-scroll")
        self._auto_scroll_checkbox.setAccessibleName("Auto-scroll toggle")
        self._auto_scroll_checkbox.setAccessibleDescription("Automatically scroll to show new log messages")
        self._auto_scroll_checkbox.setToolTip("Automatically scroll to show new messages (Alt+A)")
        self._auto_scroll_checkbox.setChecked(True)
        self._auto_scroll_checkbox.toggled.connect(self._on_auto_scroll_toggled)
        layout.addWidget(self._auto_scroll_checkbox)

        # Jump to end button (hidden when auto-scroll is on)
        self._jump_to_end_btn = QPushButton("Jump to End")
        self._jump_to_end_btn.setAccessibleName("Jump to end")
        self._jump_to_end_btn.setAccessibleDescription("Jump to the end of the log")
        self._jump_to_end_btn.setToolTip("Jump to the end of the log (Ctrl+End)")
        self._jump_to_end_btn.clicked.connect(self.jumpToEndRequested.emit)
        self._jump_to_end_btn.setVisible(False)  # Hidden when auto-scroll is on
        layout.addWidget(self._jump_to_end_btn)

        # Auto-scroll status indicator
        self._auto_scroll_status = QLabel()
        self._auto_scroll_status.setStyleSheet(
            f"QLabel {{ color: {AccessiblePalette.LOG_WARNING_TEXT}; font-style: italic; }}"
        )
        self._auto_scroll_status.setVisible(False)  # Hidden by default
        layout.addWidget(self._auto_scroll_status)

    def _setup_keyboard_shortcuts(self) -> None:
        """Set up keyboard shortcuts."""
        # Search shortcuts
        search_action = QAction(self)
        search_action.setShortcut(QKeySequence("Ctrl+F"))
        search_action.triggered.connect(self._search_input.setFocus)
        self.addAction(search_action)

        clear_search_action = QAction(self)
        clear_search_action.setShortcut(QKeySequence("Escape"))
        clear_search_action.triggered.connect(self._on_clear_search)
        self.addAction(clear_search_action)

        next_match_action = QAction(self)
        next_match_action.setShortcut(QKeySequence("F3"))
        next_match_action.triggered.connect(self.nextMatchRequested.emit)
        self.addAction(next_match_action)

        next_match_alt_action = QAction(self)
        next_match_alt_action.setShortcut(QKeySequence("Ctrl+G"))
        next_match_alt_action.triggered.connect(self.nextMatchRequested.emit)
        self.addAction(next_match_alt_action)

        prev_match_action = QAction(self)
        prev_match_action.setShortcut(QKeySequence("Shift+F3"))
        prev_match_action.triggered.connect(self.previousMatchRequested.emit)
        self.addAction(prev_match_action)

        prev_match_alt_action = QAction(self)
        prev_match_alt_action.setShortcut(QKeySequence("Ctrl+Shift+G"))
        prev_match_alt_action.triggered.connect(self.previousMatchRequested.emit)
        self.addAction(prev_match_alt_action)

        # Auto-scroll shortcuts
        auto_scroll_action = QAction(self)
        auto_scroll_action.setShortcut(QKeySequence("Alt+A"))
        auto_scroll_action.triggered.connect(lambda: self._auto_scroll_checkbox.toggle())
        self.addAction(auto_scroll_action)

        jump_to_end_action = QAction(self)
        jump_to_end_action.setShortcut(QKeySequence("Ctrl+End"))
        jump_to_end_action.triggered.connect(self.jumpToEndRequested.emit)
        self.addAction(jump_to_end_action)

    def _load_settings(self) -> None:
        """Load settings from QSettings."""
        settings = QSettings()

        # Load level filter
        level_filter = settings.value("ui/logConsole/levelFilter", "All")
        if isinstance(level_filter, str):
            index = self._level_filter.findText(level_filter)
            if index >= 0:
                self._level_filter.setCurrentIndex(index)

        # Load auto-scroll state
        auto_scroll = settings.value("ui/logConsole/autoScrollEnabled", True, type=bool)
        if isinstance(auto_scroll, bool):
            self._auto_scroll_checkbox.setChecked(auto_scroll)
            self._on_auto_scroll_toggled(auto_scroll)

    def _on_level_filter_changed(self, level: str) -> None:
        """Handle level filter changes."""
        # Save to settings
        settings = QSettings()
        settings.setValue("ui/logConsole/levelFilter", level)

        # Emit signal
        self.levelFilterChanged.emit(level)

    def _on_clear_search(self) -> None:
        """Handle clear search button click."""
        self._search_input.clear()
        self.searchCleared.emit()

    def _on_auto_scroll_toggled(self, enabled: bool) -> None:
        """Handle auto-scroll toggle."""
        # Save to settings
        settings = QSettings()
        settings.setValue("ui/logConsole/autoScrollEnabled", enabled)

        # Update UI visibility
        self._jump_to_end_btn.setVisible(not enabled)

        if enabled:
            self._auto_scroll_status.setVisible(False)
        else:
            self._auto_scroll_status.setText("Auto-scroll paused")
            self._auto_scroll_status.setVisible(True)

        # Emit signal
        self.autoScrollToggled.emit(enabled)

    def update_match_counter(self, current_match: int, total_matches: int) -> None:
        """
        Update the match counter display.

        Args:
            current_match: Current match index (1-based, 0 if no matches)
            total_matches: Total number of matches
        """
        if total_matches == 0:
            self._match_counter.setText("")
        else:
            self._match_counter.setText(f"{current_match}/{total_matches}")

    def get_level_filter(self) -> str:
        """Get the current level filter."""
        return self._level_filter.currentText()

    def get_search_text(self) -> str:
        """Get the current search text."""
        return self._search_input.text()

    def is_auto_scroll_enabled(self) -> bool:
        """Check if auto-scroll is enabled."""
        return self._auto_scroll_checkbox.isChecked()

    def focus_search_input(self) -> None:
        """Set focus to the search input."""
        self._search_input.setFocus()
        self._search_input.selectAll()
