"""
Search functionality for the LogConsole widget.

This module provides search and highlighting capabilities for log console text.
"""

from PySide6.QtCore import QRegularExpression, QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QTextEdit, QWidget

from gui.utils.styling import create_search_highlight_format


class LogSearchManager(QWidget):
    """
    Manages search functionality for a QTextEdit log console.

    Provides case-insensitive search with highlighting and navigation
    between matches.
    """

    def __init__(self, text_edit: QTextEdit, debounce_ms: int = 150) -> None:
        """
        Initialize the search manager.

        Args:
            text_edit: The QTextEdit to search within
            debounce_ms: Debounce delay for search input (0 to disable)
        """
        super().__init__()
        self._text_edit = text_edit
        self._search_text: str | None = None
        self._search_matches: list[tuple[int, int]] = []
        self._current_match_index = -1

        # Debounce timer for search input
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._apply_search_highlights)
        self._debounce_ms = debounce_ms

    def set_search_text(self, text: str) -> None:
        """
        Set the search text and trigger highlighting.

        Args:
            text: The text to search for (empty string clears search)
        """
        text = text.strip()
        self._search_text = text if text else None
        self._current_match_index = -1

        if self._debounce_ms > 0:
            self._search_timer.stop()
            self._search_timer.start(self._debounce_ms)
        else:
            self._apply_search_highlights()

    def force_search(self) -> None:
        """Force immediate search without debounce."""
        self._search_timer.stop()
        self._apply_search_highlights()

    def clear_search(self) -> None:
        """Clear the current search and remove all highlights."""
        self._search_text = None
        self._current_match_index = -1
        self._search_matches.clear()
        self._text_edit.setExtraSelections([])

    def get_search_text(self) -> str | None:
        """Get the current search text."""
        return self._search_text

    def get_match_count(self) -> int:
        """Get the number of search matches."""
        return len(self._search_matches)

    def get_current_match_index(self) -> int:
        """Get the current match index (0-based, -1 if no matches)."""
        return self._current_match_index

    def navigate_to_next_match(self) -> bool:
        """
        Navigate to the next search match.

        Returns:
            True if navigation was successful
        """
        if not self._search_matches:
            return False

        self._current_match_index = (self._current_match_index + 1) % len(self._search_matches)
        self._highlight_current_match()
        return True

    def navigate_to_previous_match(self) -> bool:
        """
        Navigate to the previous search match.

        Returns:
            True if navigation was successful
        """
        if not self._search_matches:
            return False

        self._current_match_index = (self._current_match_index - 1) % len(self._search_matches)
        self._highlight_current_match()
        return True

    def refresh_highlights(self) -> None:
        """Refresh search highlights after text content changes."""
        if self._search_text:
            # Use a timer to ensure the document layout is ready
            QTimer.singleShot(0, self._apply_search_highlights)

    def _apply_search_highlights(self) -> None:
        """Apply search highlights to all matches in the text."""
        if not self._search_text:
            self.clear_search()
            return

        document_text = self._text_edit.document().toPlainText()
        if not document_text:
            self._search_matches.clear()
            self._text_edit.setExtraSelections([])
            return

        # Create case-insensitive regex
        escaped_text = QRegularExpression.escape(self._search_text)
        regex = QRegularExpression(escaped_text, QRegularExpression.PatternOption.CaseInsensitiveOption)

        # Find all matches
        self._search_matches.clear()
        match_iterator = regex.globalMatch(document_text)

        while match_iterator.hasNext():
            match = match_iterator.next()
            start = match.capturedStart()
            length = match.capturedLength()
            self._search_matches.append((start, length))

        # Create highlight selections
        selections = []
        highlight_format = create_search_highlight_format(is_active=False)

        for start, length in self._search_matches:
            cursor = QTextCursor(self._text_edit.document())
            cursor.setPosition(start)
            cursor.setPosition(start + length, QTextCursor.MoveMode.KeepAnchor)

            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            selection.format = highlight_format
            selections.append(selection)

        self._text_edit.setExtraSelections(selections)

        # Set current match index
        if self._search_matches:
            if self._current_match_index < 0 or self._current_match_index >= len(self._search_matches):
                self._current_match_index = 0
        else:
            self._current_match_index = -1

    def _highlight_current_match(self) -> None:
        """Highlight the current match with active styling and center it in view."""
        if not self._search_matches or self._current_match_index < 0:
            return

        # Re-create all selections with current match highlighted differently
        selections = []
        normal_format = create_search_highlight_format(is_active=False)
        active_format = create_search_highlight_format(is_active=True)

        for i, (start, length) in enumerate(self._search_matches):
            cursor = QTextCursor(self._text_edit.document())
            cursor.setPosition(start)
            cursor.setPosition(start + length, QTextCursor.MoveMode.KeepAnchor)

            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            selection.format = active_format if i == self._current_match_index else normal_format
            selections.append(selection)

        self._text_edit.setExtraSelections(selections)

        # Center the current match in the view
        if self._current_match_index < len(self._search_matches):
            start, length = self._search_matches[self._current_match_index]
            cursor = QTextCursor(self._text_edit.document())
            cursor.setPosition(start)
            cursor.setPosition(start + length, QTextCursor.MoveMode.KeepAnchor)
            self._text_edit.setTextCursor(cursor)
            self._text_edit.ensureCursorVisible()
