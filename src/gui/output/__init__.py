"""Output management components for the PDF2Foundry GUI.

This module contains components for managing output directories,
validation, and file operations.
"""

from .output_folder_controller import OutputFolderController, ValidationResult

__all__ = [
    "OutputFolderController",
    "ValidationResult",
]
