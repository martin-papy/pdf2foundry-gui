"""
Tests for the LogConsole widget.
"""

import pytest
from PySide6.QtCore import QDateTime

from gui.widgets.log_console import LogConsole, LogEntry


@pytest.fixture
def log_console(qtbot):
    """Create a LogConsole widget for testing."""
    console = LogConsole(max_entries=100, search_debounce_ms=0)  # No debounce for tests
    qtbot.addWidget(console)
    # Reset to "All" filter for consistent testing
    console._current_filter = "All"
    console._filter_combo.setCurrentText("All")
    return console


class TestLogConsoleInitialization:
    """Test LogConsole initialization."""

    def test_console_creation(self, log_console):
        """Test that LogConsole can be created."""
        assert log_console is not None
        assert log_console.get_max_entries() == 100
        assert log_console.get_entry_count() == 0
        assert log_console.is_auto_scroll_enabled() is True

    def test_default_max_entries(self, qtbot):
        """Test default maximum entries."""
        console = LogConsole(search_debounce_ms=0)
        qtbot.addWidget(console)
        assert console.get_max_entries() == 10000


class TestLogConsoleBasicFunctionality:
    """Test basic LogConsole functionality."""

    def test_append_log_info(self, log_console):
        """Test appending INFO level log."""
        log_console.append_log("INFO", "Test message")
        assert log_console.get_entry_count() == 1

        entries = log_console.get_entries()
        assert len(entries) == 1
        assert entries[0].level == "INFO"
        assert entries[0].message == "Test message"

    def test_append_log_warning(self, log_console):
        """Test appending WARNING level log."""
        log_console.append_log("WARNING", "Warning message")
        assert log_console.get_entry_count() == 1

        entries = log_console.get_entries()
        assert entries[0].level == "WARNING"
        assert entries[0].message == "Warning message"

    def test_append_log_error(self, log_console):
        """Test appending ERROR level log."""
        log_console.append_log("ERROR", "Error message")
        assert log_console.get_entry_count() == 1

        entries = log_console.get_entries()
        assert entries[0].level == "ERROR"
        assert entries[0].message == "Error message"

    def test_append_log_with_timestamp(self, log_console):
        """Test appending log with custom timestamp."""
        timestamp = QDateTime.currentDateTime()
        log_console.append_log("INFO", "Test message", timestamp)

        entries = log_console.get_entries()
        assert entries[0].timestamp == timestamp

    def test_multiple_log_entries(self, log_console):
        """Test appending multiple log entries."""
        log_console.append_log("INFO", "First message")
        log_console.append_log("WARNING", "Second message")
        log_console.append_log("ERROR", "Third message")

        assert log_console.get_entry_count() == 3

        entries = log_console.get_entries()
        assert entries[0].message == "First message"
        assert entries[1].message == "Second message"
        assert entries[2].message == "Third message"

    def test_clear_logs(self, log_console):
        """Test clearing all logs."""
        log_console.append_log("INFO", "Test message")
        assert log_console.get_entry_count() == 1

        log_console.clear()
        assert log_console.get_entry_count() == 0
        assert len(log_console.get_entries()) == 0


class TestLogConsoleAutoScroll:
    """Test LogConsole auto-scroll functionality."""

    def test_auto_scroll_enabled_by_default(self, log_console):
        """Test that auto-scroll is enabled by default."""
        assert log_console.is_auto_scroll_enabled() is True

    def test_pause_auto_scroll(self, log_console):
        """Test pausing auto-scroll."""
        log_console.pause_auto_scroll(True)
        assert log_console.is_auto_scroll_enabled() is False

        log_console.pause_auto_scroll(False)
        assert log_console.is_auto_scroll_enabled() is True


class TestLogConsoleRingBuffer:
    """Test LogConsole ring buffer functionality."""

    def test_ring_buffer_limit(self, qtbot):
        """Test that ring buffer respects maximum entries."""
        console = LogConsole(max_entries=3, search_debounce_ms=0)
        qtbot.addWidget(console)

        # Add more entries than the limit
        console.append_log("INFO", "Message 1")
        console.append_log("INFO", "Message 2")
        console.append_log("INFO", "Message 3")
        console.append_log("INFO", "Message 4")  # Should push out Message 1

        assert console.get_entry_count() == 3
        entries = console.get_entries()

        # Should contain messages 2, 3, 4 (oldest removed)
        assert entries[0].message == "Message 2"
        assert entries[1].message == "Message 3"
        assert entries[2].message == "Message 4"


class TestLogConsoleSignals:
    """Test LogConsole signals."""

    def test_entry_count_changed_signal(self, log_console, qtbot):
        """Test that entryCountChanged signal is emitted."""
        with qtbot.waitSignal(log_console.entryCountChanged) as blocker:
            log_console.append_log("INFO", "Test message")

        assert blocker.args == [1]

    def test_entry_count_changed_on_clear(self, log_console, qtbot):
        """Test that entryCountChanged signal is emitted on clear."""
        log_console.append_log("INFO", "Test message")

        with qtbot.waitSignal(log_console.entryCountChanged) as blocker:
            log_console.clear()

        assert blocker.args == [0]


class TestLogConsoleFiltering:
    """Test LogConsole filtering functionality."""

    def test_filter_all_shows_all_entries(self, log_console):
        """Test that 'All' filter shows all entries."""
        log_console.append_log("INFO", "Info message")
        log_console.append_log("WARNING", "Warning message")
        log_console.append_log("ERROR", "Error message")

        # Should show all entries by default
        text_content = log_console._text_edit.toPlainText()
        assert "Info message" in text_content
        assert "Warning message" in text_content
        assert "Error message" in text_content

    def test_filter_info_shows_only_info(self, log_console):
        """Test that INFO filter shows only INFO entries."""
        log_console.append_log("INFO", "Info message")
        log_console.append_log("WARNING", "Warning message")
        log_console.append_log("ERROR", "Error message")

        # Change filter to INFO
        log_console._filter_combo.setCurrentText("INFO")

        text_content = log_console._text_edit.toPlainText()
        assert "Info message" in text_content
        assert "Warning message" not in text_content
        assert "Error message" not in text_content

    def test_filter_warning_shows_only_warning(self, log_console):
        """Test that WARNING filter shows only WARNING entries."""
        log_console.append_log("INFO", "Info message")
        log_console.append_log("WARNING", "Warning message")
        log_console.append_log("ERROR", "Error message")

        # Change filter to WARNING
        log_console._filter_combo.setCurrentText("WARNING")

        text_content = log_console._text_edit.toPlainText()
        assert "Info message" not in text_content
        assert "Warning message" in text_content
        assert "Error message" not in text_content

    def test_filter_error_shows_only_error(self, log_console):
        """Test that ERROR filter shows only ERROR entries."""
        log_console.append_log("INFO", "Info message")
        log_console.append_log("WARNING", "Warning message")
        log_console.append_log("ERROR", "Error message")

        # Change filter to ERROR
        log_console._filter_combo.setCurrentText("ERROR")

        text_content = log_console._text_edit.toPlainText()
        assert "Info message" not in text_content
        assert "Warning message" not in text_content
        assert "Error message" in text_content


class TestLogConsoleSearch:
    """Test LogConsole search functionality."""

    def test_search_finds_matches(self, log_console):
        """Test that search finds and highlights matches."""
        log_console.append_log("INFO", "This is a test message")
        log_console.append_log("WARNING", "Another test entry")
        log_console.append_log("ERROR", "No match here")

        # Perform search
        log_console._search_input.setText("test")
        log_console.force_search()

        # Should find 2 matches
        assert len(log_console._search_matches) == 2
        assert log_console._match_label.text() == "1/2"

    def test_search_navigation(self, log_console):
        """Test search navigation between matches."""
        log_console.append_log("INFO", "First test message")
        log_console.append_log("WARNING", "Second test entry")

        # Perform search
        log_console._search_input.setText("test")
        log_console.force_search()

        # Should be at first match
        assert log_console._current_match_index == 0
        assert log_console._match_label.text() == "1/2"

        # Go to next match
        log_console._go_to_next_match()
        assert log_console._current_match_index == 1
        assert log_console._match_label.text() == "2/2"

        # Go to next (should wrap to first)
        log_console._go_to_next_match()
        assert log_console._current_match_index == 0
        assert log_console._match_label.text() == "1/2"

    def test_search_clear(self, log_console):
        """Test clearing search."""
        log_console.append_log("INFO", "Test message")

        # Perform search
        log_console._search_input.setText("test")
        log_console.force_search()

        assert len(log_console._search_matches) == 1

        # Clear search
        log_console._clear_search()

        assert log_console._search_input.text() == ""
        assert len(log_console._search_matches) == 0
        assert log_console._match_label.text() == ""

    def test_search_no_matches(self, log_console):
        """Test search with no matches."""
        log_console.append_log("INFO", "Test message")

        # Search for something that doesn't exist
        log_console._search_input.setText("nonexistent")
        log_console.force_search()

        assert len(log_console._search_matches) == 0
        assert log_console._match_label.text() == "0/0"
        assert not log_console._next_btn.isEnabled()
        assert not log_console._prev_btn.isEnabled()


class TestLogConsoleIntegration:
    """Test LogConsole integration features."""

    def test_filter_and_search_together(self, log_console):
        """Test filtering and searching work together."""
        log_console.append_log("INFO", "Info test message")
        log_console.append_log("WARNING", "Warning test entry")
        log_console.append_log("ERROR", "Error message")

        # Filter to INFO only
        log_console._filter_combo.setCurrentText("INFO")

        # Search for "test"
        log_console._search_input.setText("test")
        log_console.force_search()

        # Should only find match in INFO entries
        assert len(log_console._search_matches) == 1
        text_content = log_console._text_edit.toPlainText()
        assert "Info test message" in text_content
        assert "Warning test entry" not in text_content

    def test_settings_persistence(self, qtbot):
        """Test that filter settings are persisted."""
        console1 = LogConsole(search_debounce_ms=0)
        qtbot.addWidget(console1)

        # Change filter
        console1._filter_combo.setCurrentText("ERROR")

        # Create new console - should load saved filter
        console2 = LogConsole(search_debounce_ms=0)
        qtbot.addWidget(console2)

        assert console2._filter_combo.currentText() == "ERROR"
        assert console2._current_filter == "ERROR"


class TestLogEntry:
    """Test LogEntry named tuple."""

    def test_log_entry_creation(self):
        """Test LogEntry creation."""
        timestamp = QDateTime.currentDateTime()
        entry = LogEntry(level="INFO", message="Test message", timestamp=timestamp)

        assert entry.level == "INFO"
        assert entry.message == "Test message"
        assert entry.timestamp == timestamp
