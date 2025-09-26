"""
LogConsole widget for displaying formatted log messages with auto-scroll.

This module provides a reusable LogConsole widget that wraps a QTextEdit
to display timestamped log messages with level-based formatting and
auto-scroll functionality.
"""

from collections import deque
from typing import Any, ClassVar, NamedTuple

from PySide6.QtCore import QDateTime, QRegularExpression, QSettings, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget


class LogEntry(NamedTuple):
    """Structured log entry for the ring buffer."""

    level: str
    message: str
    timestamp: QDateTime


class LogConsole(QWidget):
    """
    A console widget for displaying formatted log messages.

    Features:
    - Level-based formatting (INFO, WARNING, ERROR)
    - Timestamped entries
    - Auto-scroll functionality
    - Ring buffer for memory management
    - Configurable maximum entries
    """

    # Signals
    entryCountChanged = Signal(int)

    # Log level formatting
    LOG_FORMATS: ClassVar[dict[str, dict[str, Any]]] = {
        "INFO": {
            "color": QColor("#666666"),  # Gray
            "bold": False,
        },
        "WARNING": {
            "color": QColor("#ff9800"),  # Orange
            "bold": True,
        },
        "ERROR": {
            "color": QColor("#f44336"),  # Red
            "bold": True,
        },
    }

    def __init__(self, max_entries: int = 10000, search_debounce_ms: int = 150, parent: QWidget | None = None) -> None:
        """
        Initialize the LogConsole widget.

        Args:
            max_entries: Maximum number of log entries to keep in memory
            search_debounce_ms: Debounce delay for search (0 to disable)
            parent: Parent widget
        """
        super().__init__(parent)

        self._max_entries = max_entries
        self._auto_scroll_enabled = True
        self._entries: deque[LogEntry] = deque(maxlen=max_entries)

        # Search and filtering state
        self._current_filter = "All"
        self._search_text = ""
        self._search_matches: list[int] = []
        self._current_match_index = -1

        # Settings for persistence
        self._settings = QSettings("PDF2Foundry", "LogConsole")

        # Debounce timer for search
        self._search_debounce_ms = search_debounce_ms
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._perform_search)

        self._setup_ui()
        self._load_settings()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Create controls row
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(10)

        # Filter combo box
        filter_label = QLabel("Filter:")
        controls_layout.addWidget(filter_label)

        self._filter_combo = QComboBox()
        self._filter_combo.addItems(["All", "INFO", "WARNING", "ERROR"])
        self._filter_combo.currentTextChanged.connect(self._on_filter_changed)
        controls_layout.addWidget(self._filter_combo)

        # Search controls
        search_label = QLabel("Search:")
        controls_layout.addWidget(search_label)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search logs...")
        self._search_input.textChanged.connect(self._on_search_text_changed)
        controls_layout.addWidget(self._search_input)

        # Clear search button
        self._clear_search_btn = QPushButton("✕")
        self._clear_search_btn.setMaximumWidth(30)
        self._clear_search_btn.setToolTip("Clear search")
        self._clear_search_btn.clicked.connect(self._clear_search)
        controls_layout.addWidget(self._clear_search_btn)

        # Navigation buttons
        self._prev_btn = QPushButton("↑")
        self._prev_btn.setMaximumWidth(30)
        self._prev_btn.setToolTip("Previous match (Shift+F3)")
        self._prev_btn.clicked.connect(self._go_to_previous_match)
        self._prev_btn.setEnabled(False)
        controls_layout.addWidget(self._prev_btn)

        self._next_btn = QPushButton("↓")
        self._next_btn.setMaximumWidth(30)
        self._next_btn.setToolTip("Next match (F3)")
        self._next_btn.clicked.connect(self._go_to_next_match)
        self._next_btn.setEnabled(False)
        controls_layout.addWidget(self._next_btn)

        # Match count label
        self._match_label = QLabel("")
        controls_layout.addWidget(self._match_label)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # Create text edit
        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self._text_edit.setStyleSheet(
            """
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
            }
        """
        )

        layout.addWidget(self._text_edit)

    def append_log(self, level: str, message: str, timestamp: QDateTime | None = None) -> None:
        """
        Append a log message with formatting.

        Args:
            level: Log level (INFO, WARNING, ERROR)
            message: Log message text
            timestamp: Optional timestamp (defaults to current time)
        """
        if timestamp is None:
            timestamp = QDateTime.currentDateTime()

        # Create log entry
        entry = LogEntry(level=level, message=message, timestamp=timestamp)
        self._entries.append(entry)

        # Refresh display to show new entry (if it matches current filter)
        self._refresh_display()

        # Emit signal for entry count change
        self.entryCountChanged.emit(len(self._entries))

    def _get_text_format(self, level: str) -> QTextCharFormat:
        """
        Get the text format for a given log level.

        Args:
            level: Log level string

        Returns:
            QTextCharFormat with appropriate styling
        """
        format_config = self.LOG_FORMATS.get(level, self.LOG_FORMATS["INFO"])

        text_format = QTextCharFormat()
        text_format.setForeground(format_config["color"])

        if format_config["bold"]:
            font = QFont()
            font.setBold(True)
            text_format.setFont(font)

        return text_format

    def clear(self) -> None:
        """Clear all log entries and the display."""
        self._entries.clear()
        self._text_edit.clear()
        self._clear_search_highlights()
        self._search_matches.clear()
        self._current_match_index = -1
        self._update_search_ui()
        self.entryCountChanged.emit(0)

    def pause_auto_scroll(self, paused: bool) -> None:
        """
        Pause or resume auto-scroll functionality.

        Args:
            paused: True to pause auto-scroll, False to resume
        """
        self._auto_scroll_enabled = not paused

    def is_auto_scroll_enabled(self) -> bool:
        """Check if auto-scroll is currently enabled."""
        return self._auto_scroll_enabled

    def get_entry_count(self) -> int:
        """Get the current number of log entries."""
        return len(self._entries)

    def get_max_entries(self) -> int:
        """Get the maximum number of entries."""
        return self._max_entries

    def get_entries(self) -> list[LogEntry]:
        """Get a copy of all current log entries."""
        return list(self._entries)

    def scroll_to_bottom(self) -> None:
        """Manually scroll to the bottom of the log."""
        scrollbar = self._text_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    # Filtering and search methods

    def _should_show_entry(self, entry: LogEntry) -> bool:
        """Check if an entry should be shown based on current filter."""
        if self._current_filter == "All":
            return True
        return entry.level == self._current_filter

    def _get_filtered_entries(self) -> list[LogEntry]:
        """Get entries that match the current filter."""
        if self._current_filter == "All":
            return list(self._entries)
        return [entry for entry in self._entries if entry.level == self._current_filter]

    def _refresh_display(self) -> None:
        """Refresh the text display based on current filter and search."""
        # Clear current display
        self._text_edit.clear()

        # Get filtered entries
        filtered_entries = self._get_filtered_entries()

        # Add each entry with formatting
        for entry in filtered_entries:
            time_str = entry.timestamp.toString("hh:mm:ss")
            formatted_message = f"[{time_str}] [{entry.level}] {entry.message}"

            # Get text format for this level
            text_format = self._get_text_format(entry.level)

            # Move cursor to end and insert formatted text
            cursor = self._text_edit.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(formatted_message + "\n", text_format)

        # Auto-scroll if enabled
        if self._auto_scroll_enabled:
            self._text_edit.ensureCursorVisible()

        # Re-apply search highlighting if there's a search term
        if self._search_text:
            # Use a timer to ensure the document layout is ready
            QTimer.singleShot(0, self._apply_search_highlights)

    def _on_filter_changed(self, filter_text: str) -> None:
        """Handle filter combo box change."""
        self._current_filter = filter_text
        self._refresh_display()
        self._save_settings()

    def _on_search_text_changed(self, text: str) -> None:
        """Handle search input text change with debouncing."""
        self._search_text = text.strip()
        self._search_timer.stop()

        if self._search_debounce_ms > 0:
            self._search_timer.start(self._search_debounce_ms)
        else:
            self._perform_search()

    def _perform_search(self) -> None:
        """Perform the actual search and highlight matches."""
        # Clear previous search highlights
        self._clear_search_highlights()
        self._search_matches.clear()
        self._current_match_index = -1

        if not self._search_text:
            self._update_search_ui()
            return

        # Get the plain text content
        text_content = self._text_edit.document().toPlainText()

        # Create case-insensitive regular expression
        escaped_search = QRegularExpression.escape(self._search_text)
        regex = QRegularExpression(escaped_search)
        regex.setPatternOptions(QRegularExpression.PatternOption.CaseInsensitiveOption)

        # Find all matches
        match_iterator = regex.globalMatch(text_content)
        while match_iterator.hasNext():
            match = match_iterator.next()
            self._search_matches.append(match.capturedStart())

        # Highlight all matches
        self._highlight_search_matches()

        # Go to first match if any
        if self._search_matches:
            self._current_match_index = 0
            self._go_to_current_match()

        self._update_search_ui()

    def _apply_search_highlights(self) -> None:
        """Apply search highlights after display refresh."""
        if not self._search_text:
            return

        # Clear previous matches and highlights
        self._clear_search_highlights()
        self._search_matches.clear()
        self._current_match_index = -1

        # Get the plain text content
        text_content = self._text_edit.document().toPlainText()

        # Create case-insensitive regular expression
        escaped_search = QRegularExpression.escape(self._search_text)
        regex = QRegularExpression(escaped_search)
        regex.setPatternOptions(QRegularExpression.PatternOption.CaseInsensitiveOption)

        # Find all matches
        match_iterator = regex.globalMatch(text_content)
        while match_iterator.hasNext():
            match = match_iterator.next()
            self._search_matches.append(match.capturedStart())

        # Highlight all matches
        self._highlight_search_matches()

        # Go to first match if any
        if self._search_matches:
            self._current_match_index = 0
            self._go_to_current_match()

        self._update_search_ui()

    def force_search(self) -> None:
        """Force immediate search without debounce (for testing)."""
        self._perform_search()

    def _highlight_search_matches(self) -> None:
        """Highlight all search matches."""
        if not self._search_matches:
            return

        # Create highlight format
        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QColor("#ffeb3b"))  # Yellow highlight
        highlight_format.setForeground(QColor("#000000"))  # Black text

        # Apply highlights
        extra_selections = []
        for match_pos in self._search_matches:
            selection = QTextEdit.ExtraSelection()
            cursor = self._text_edit.textCursor()
            cursor.setPosition(match_pos)
            cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, len(self._search_text))
            selection.cursor = cursor
            selection.format = highlight_format
            extra_selections.append(selection)

        self._text_edit.setExtraSelections(extra_selections)

    def _clear_search_highlights(self) -> None:
        """Clear all search highlights."""
        self._text_edit.setExtraSelections([])

    def _go_to_current_match(self) -> None:
        """Navigate to the current search match."""
        if not self._search_matches or self._current_match_index < 0:
            return

        match_pos = self._search_matches[self._current_match_index]
        cursor = self._text_edit.textCursor()
        cursor.setPosition(match_pos)
        cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, len(self._search_text))
        self._text_edit.setTextCursor(cursor)
        self._text_edit.ensureCursorVisible()

    def _go_to_next_match(self) -> None:
        """Navigate to the next search match."""
        if not self._search_matches:
            return

        self._current_match_index = (self._current_match_index + 1) % len(self._search_matches)
        self._go_to_current_match()
        self._update_search_ui()

    def _go_to_previous_match(self) -> None:
        """Navigate to the previous search match."""
        if not self._search_matches:
            return

        self._current_match_index = (self._current_match_index - 1) % len(self._search_matches)
        self._go_to_current_match()
        self._update_search_ui()

    def _clear_search(self) -> None:
        """Clear the search input and highlights."""
        self._search_input.clear()
        self._search_text = ""
        self._clear_search_highlights()
        self._search_matches.clear()
        self._current_match_index = -1
        self._update_search_ui()

    def _update_search_ui(self) -> None:
        """Update search-related UI elements."""
        has_matches = len(self._search_matches) > 0

        # Enable/disable navigation buttons
        self._prev_btn.setEnabled(has_matches)
        self._next_btn.setEnabled(has_matches)

        # Update match count label
        if has_matches:
            current = self._current_match_index + 1 if self._current_match_index >= 0 else 0
            self._match_label.setText(f"{current}/{len(self._search_matches)}")
        else:
            self._match_label.setText("" if not self._search_text else "0/0")

    def _load_settings(self) -> None:
        """Load settings from QSettings."""
        saved_filter: str = str(self._settings.value("filter", "All", type=str))
        if saved_filter in ["All", "INFO", "WARNING", "ERROR"]:
            self._current_filter = saved_filter
            self._filter_combo.setCurrentText(saved_filter)
        else:
            # Fallback to "All" if invalid setting
            self._current_filter = "All"
            self._filter_combo.setCurrentText("All")

    def _save_settings(self) -> None:
        """Save settings to QSettings."""
        self._settings.setValue("filter", self._current_filter)
