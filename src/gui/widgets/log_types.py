"""
Log entry types and utilities for the LogConsole widget.

This module provides data structures and utilities for managing log entries
in the console widget.
"""

from typing import NamedTuple

from PySide6.QtCore import QDateTime


class LogEntry(NamedTuple):
    """Structured log entry for the ring buffer."""

    level: str
    message: str
    timestamp: QDateTime


def format_log_entry(entry: LogEntry) -> str:
    """
    Format a log entry for display.

    Args:
        entry: The log entry to format

    Returns:
        Formatted string with timestamp and message
    """
    timestamp_str = entry.timestamp.toString("hh:mm:ss")
    return f"[{timestamp_str}] {entry.message}"


def should_show_entry(entry: LogEntry, level_filter: str) -> bool:
    """
    Check if an entry should be shown based on the level filter.

    Args:
        entry: The log entry to check
        level_filter: The current level filter ("All", "INFO", "WARNING", "ERROR")

    Returns:
        True if the entry should be shown
    """
    return level_filter == "All" or entry.level == level_filter
