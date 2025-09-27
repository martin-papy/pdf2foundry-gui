"""
Conversion state management for the PDF2Foundry GUI.

This module defines the conversion states used throughout the application
to ensure consistent state management between UI and backend components.
"""

from enum import Enum, auto


class ConversionState(Enum):
    """
    Enumeration of conversion states.

    These states represent the current status of the conversion process
    and are used to coordinate UI updates and backend operations.
    """

    IDLE = auto()  # No conversion running, ready to start
    RUNNING = auto()  # Conversion in progress
    COMPLETED = auto()  # Conversion completed successfully
    ERROR = auto()  # Conversion failed with error
