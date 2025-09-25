"""
Settings dialog for the PDF2Foundry GUI application.
"""

import logging
import os
import re
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.config_manager import ConfigManager
from core.preset_manager import PresetError, PresetManager
from gui.widgets.directory_selector import OutputDirectorySelector

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """
    Settings dialog with tabbed interface for PDF2Foundry CLI options.

    Provides organized access to all CLI options through General, Conversion,
    and Debug tabs with proper validation and persistence.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Configuration management
        self._config_manager = ConfigManager()
        self._preset_manager = PresetManager()

        # State tracking
        self._dirty = False
        self._initializing = True  # Flag to prevent marking dirty during initialization
        self._export_debug_path: str | None = None

        # Set up the dialog
        self._setup_dialog()

        # Create the UI
        self._setup_ui()

        # Connect signals
        self._connect_signals()

        # Load settings
        self.loadSettings()

        # Initialization complete - now allow dirty tracking
        self._initializing = False

    # Validation helper methods
    def _normalize_path(self, path: str) -> str:
        """Normalize a file path for cross-platform compatibility."""
        if not path.strip():
            return ""
        return str(Path(path).expanduser().resolve())

    def _is_dir_writable(self, path: str) -> bool:
        """Check if a directory exists and is writable."""
        if not path:
            return False
        try:
            path_obj = Path(path)
            return path_obj.exists() and path_obj.is_dir() and os.access(path, os.W_OK | os.X_OK)
        except (OSError, ValueError):
            return False

    def _is_file_path_writable(self, path: str) -> bool:
        """Check if a file path's parent directory exists and is writable."""
        if not path:
            return True  # Empty path is valid (means don't write to file)
        try:
            parent = Path(path).parent
            return self._is_dir_writable(str(parent))
        except (OSError, ValueError):
            return False

    def _parse_pages(self, spec: str) -> list[tuple[int, int]] | None:
        """Parse page specification into list of (start, end) tuples."""
        if not spec.strip():
            return []  # Empty means all pages

        # Regex for comma-separated numbers/ranges
        pattern = r"^\s*\d+\s*(?:-\s*\d+)?(?:\s*,\s*\d+\s*(?:-\s*\d+)?)*\s*$"
        if not re.match(pattern, spec):
            return None

        ranges = []
        for part in spec.split(","):
            part = part.strip()
            if "-" in part:
                start_str, end_str = part.split("-", 1)
                try:
                    start = int(start_str.strip())
                    end = int(end_str.strip())
                    if start <= 0 or end <= 0 or start > end:
                        return None
                    ranges.append((start, end))
                except ValueError:
                    return None
            else:
                try:
                    page = int(part)
                    if page <= 0:
                        return None
                    ranges.append((page, page))
                except ValueError:
                    return None

        return ranges

    def _set_field_error(self, widget: QWidget, message: str) -> None:
        """Mark a field as having an error and show feedback."""
        widget.setProperty("hasError", True)
        widget.setToolTip(f"Error: {message}")
        widget.style().polish(widget)  # Refresh styling

    def _clear_field_error(self, widget: QWidget) -> None:
        """Clear error state from a field."""
        widget.setProperty("hasError", False)
        # Restore original tooltip if it exists
        if hasattr(widget, "_original_tooltip"):
            widget.setToolTip(widget._original_tooltip)
        # Don't clear tooltip if we don't have an original - let the widget keep its default
        widget.style().polish(widget)  # Refresh styling

    def _validate_text_field(
        self, widget: QLineEdit, field_name: str, max_length: int = 128, required: bool = False
    ) -> bool:
        """Validate a text field with length and content restrictions."""
        text = widget.text().strip()

        if not text and required:
            self._set_field_error(widget, f"{field_name} is required")
            return False

        if text and len(text) > max_length:
            self._set_field_error(widget, f"{field_name} must be {max_length} characters or less")
            return False

        # Check for invalid path characters in pack name
        if field_name.lower() == "pack name" and text:
            invalid_chars = r'[\\/:*?"<>|]'
            if re.search(invalid_chars, text):
                self._set_field_error(widget, f'{field_name} cannot contain: \\ / : * ? " < > |')
                return False

        self._clear_field_error(widget)
        return True

    def _validate_path_field(self, widget: QLineEdit, field_name: str, required: bool = False) -> bool:
        """Validate a path field."""
        path = widget.text().strip()

        if not path and required:
            self._set_field_error(widget, f"{field_name} is required")
            return False

        if path:
            if field_name.lower() == "output directory":
                if not self._is_dir_writable(path):
                    self._set_field_error(widget, f"{field_name} must be an existing, writable directory")
                    return False
            else:  # Log file path
                if not self._is_file_path_writable(path):
                    self._set_field_error(widget, f"{field_name} parent directory must exist and be writable")
                    return False

        self._clear_field_error(widget)
        return True

    def _validate_pages_field(self) -> bool:
        """Validate the pages field."""
        if not hasattr(self, "pages_edit"):
            return True

        spec = self.pages_edit.text().strip()
        if not spec:
            self._clear_field_error(self.pages_edit)
            return True

        ranges = self._parse_pages(spec)
        if ranges is None:
            self._set_field_error(self.pages_edit, "Invalid page specification. Use format: 1,5-10,15")
            return False

        self._clear_field_error(self.pages_edit)
        return True

    def _update_dialog_buttons_enabled(self) -> None:
        """Update OK/Apply button states based on validation and dirty state."""
        is_valid = self.validateAll()

        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        apply_button = self.button_box.button(QDialogButtonBox.StandardButton.Apply)

        # OK button is enabled only when valid
        ok_button.setEnabled(is_valid)
        # Apply button is enabled when dirty, regardless of validation state
        # (user should be able to see validation errors when they try to apply)
        apply_button.setEnabled(self._dirty)

    def _setup_dialog(self) -> None:
        """Configure the dialog properties."""
        self.setWindowTitle("PDF2Foundry Settings")
        self.setModal(True)
        self.resize(600, 500)
        self.setMinimumSize(500, 400)

    def _setup_ui(self) -> None:
        """Create and arrange the user interface elements."""
        # Create main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Create preset controls
        preset_widget = self._create_preset_controls()
        layout.addWidget(preset_widget)

        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setAccessibleName("Settings tabs")

        # Create tabs
        self.general_tab = self._create_general_tab()
        self.conversion_tab = self._create_conversion_tab()
        self.debug_tab = self._create_debug_tab()

        # Add tabs to widget
        self.tab_widget.addTab(self.general_tab, "General")
        self.tab_widget.addTab(self.conversion_tab, "Conversion")
        self.tab_widget.addTab(self.debug_tab, "Debug")

        # Create button box
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.RestoreDefaults
        )
        self.button_box.setAccessibleName("Dialog buttons")

        # Initially disable Apply button
        self.button_box.button(QDialogButtonBox.StandardButton.Apply).setEnabled(False)

        # Add widgets to layout
        layout.addWidget(self.tab_widget)
        layout.addWidget(self.button_box)

    def _create_general_tab(self) -> QWidget:
        """Create the General tab with output naming and overwrite options."""
        tab = QWidget()
        tab.setAccessibleName("General settings")

        # Create scroll area for small screens
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        # Create content widget
        content = QWidget()
        form_layout = QFormLayout(content)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Author field
        self.author_edit = QLineEdit()
        self.author_edit.setPlaceholderText("Enter author name...")
        self.author_edit.setToolTip("Author metadata for module.json.")
        self.author_edit._original_tooltip = "Author metadata for module.json."
        self.author_edit.textChanged.connect(self._mark_dirty)
        form_layout.addRow("&Author:", self.author_edit)

        # License field
        self.license_edit = QLineEdit()
        self.license_edit.setPlaceholderText("Enter license...")
        self.license_edit.setToolTip("License string for module.json.")
        self.license_edit._original_tooltip = "License string for module.json."
        self.license_edit.textChanged.connect(self._mark_dirty)
        form_layout.addRow("&License:", self.license_edit)

        # Pack name field
        self.pack_name_edit = QLineEdit()
        self.pack_name_edit.setPlaceholderText("Will default to <mod-id>-journals")
        self.pack_name_edit.setToolTip("Compendium pack name.")
        self.pack_name_edit._original_tooltip = "Compendium pack name."
        self.pack_name_edit.textChanged.connect(self._mark_dirty)
        form_layout.addRow("&Pack Name:", self.pack_name_edit)

        # Output directory field
        self.output_dir_selector = OutputDirectorySelector()
        self.output_dir_selector.setToolTip("Where the module will be written.")
        self.output_dir_selector.pathChanged.connect(self._mark_dirty)
        form_layout.addRow("&Output Directory:", self.output_dir_selector)

        # Deterministic IDs checkbox
        self.deterministic_ids_checkbox = QCheckBox("Use deterministic IDs")
        self.deterministic_ids_checkbox.setChecked(True)  # Default ON
        self.deterministic_ids_checkbox.setToolTip("Stable SHA1-based IDs to keep links consistent.")
        self.deterministic_ids_checkbox.toggled.connect(self._mark_dirty)
        form_layout.addRow("", self.deterministic_ids_checkbox)

        scroll.setWidget(content)

        # Set up tab layout
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)

        return tab

    def _create_conversion_tab(self) -> QWidget:
        """Create the Conversion tab with conversion-related CLI options."""
        tab = QWidget()
        tab.setAccessibleName("Conversion settings")

        # Create scroll area for small screens
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        # Create content widget
        content = QWidget()
        form_layout = QFormLayout(content)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # TOC handling checkbox
        self.toc_checkbox = QCheckBox("Create Table of Contents entry")
        self.toc_checkbox.setChecked(True)  # Default ON
        self.toc_checkbox.setToolTip("Create a Table of Contents entry.")
        self.toc_checkbox.toggled.connect(self._mark_dirty)
        form_layout.addRow("", self.toc_checkbox)

        # Tables handling combo box
        self.tables_combo = QComboBox()
        self.tables_combo.addItems(["auto", "structured", "image-only"])
        self.tables_combo.setCurrentText("auto")  # Default
        self.tables_combo.setToolTip(
            "How to handle tables: auto (try structured, fallback to image), "
            "structured (always extract structure), image-only (always rasterize)."
        )
        self.tables_combo.currentTextChanged.connect(self._mark_dirty)
        form_layout.addRow("&Tables:", self.tables_combo)

        # OCR handling combo box
        self.ocr_combo = QComboBox()
        self.ocr_combo.addItems(["auto", "on", "off"])
        self.ocr_combo.setCurrentText("auto")  # Default
        self.ocr_combo.setToolTip(
            "OCR mode: auto (OCR pages with low text coverage), "
            "on (always OCR all pages), off (disable OCR). Requires Tesseract."
        )
        self.ocr_combo.currentTextChanged.connect(self._mark_dirty)
        form_layout.addRow("&OCR:", self.ocr_combo)

        # Picture descriptions checkbox
        self.picture_descriptions_checkbox = QCheckBox("Generate AI captions for images")
        self.picture_descriptions_checkbox.setChecked(False)  # Default OFF
        self.picture_descriptions_checkbox.setToolTip("Generate AI captions using a VLM (downloaded on first run).")
        self.picture_descriptions_checkbox.toggled.connect(self._mark_dirty)
        self.picture_descriptions_checkbox.toggled.connect(self._on_picture_descriptions_toggled)
        form_layout.addRow("", self.picture_descriptions_checkbox)

        # VLM repository ID field (disabled by default)
        self.vlm_repo_edit = QLineEdit()
        self.vlm_repo_edit.setPlaceholderText("e.g., microsoft/Florence-2-base")
        self.vlm_repo_edit.setToolTip("Hugging Face model ID for picture descriptions.")
        self.vlm_repo_edit.setEnabled(False)  # Disabled until picture descriptions is ON
        self.vlm_repo_edit.textChanged.connect(self._mark_dirty)
        form_layout.addRow("&VLM Model:", self.vlm_repo_edit)

        # Page range field
        self.pages_edit = QLineEdit()
        self.pages_edit.setPlaceholderText("e.g., 1-5,8,10- (leave empty for all pages)")
        tooltip_text = (
            "Page list/ranges to process. Format: comma-separated list of " "page numbers and ranges (e.g., '1,5-10,15')."
        )
        self.pages_edit.setToolTip(tooltip_text)
        self.pages_edit._original_tooltip = tooltip_text
        self.pages_edit.textChanged.connect(self._mark_dirty)
        form_layout.addRow("&Pages:", self.pages_edit)

        scroll.setWidget(content)

        # Set up tab layout
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)

        return tab

    def _create_debug_tab(self) -> QWidget:
        """Create the Debug tab with verbose logging and export options."""
        tab = QWidget()
        tab.setAccessibleName("Debug settings")

        # Create scroll area for small screens
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        # Create content widget
        content = QWidget()
        form_layout = QFormLayout(content)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Verbose logging checkbox
        self.verbose_checkbox = QCheckBox("&Verbose logging")
        self.verbose_checkbox.setChecked(False)
        self.verbose_checkbox.setToolTip(
            "Emit detailed logs for troubleshooting. May impact performance and produce large log output."
        )
        self.verbose_checkbox.toggled.connect(self._mark_dirty)
        form_layout.addRow("", self.verbose_checkbox)
        # Log level combo box
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level_combo.setCurrentText("INFO")
        self.log_level_combo.setToolTip("Select minimum severity to log. Lower levels (DEBUG) increase verbosity.")
        self.log_level_combo.currentTextChanged.connect(self._mark_dirty)
        form_layout.addRow("&Log level:", self.log_level_combo)
        # Dry run checkbox
        self.dry_run_checkbox = QCheckBox("&Dry run")
        self.dry_run_checkbox.setChecked(False)
        self.dry_run_checkbox.setToolTip("Simulate actions without making changes. Useful for verifying configuration.")
        self.dry_run_checkbox.toggled.connect(self._mark_dirty)
        form_layout.addRow("", self.dry_run_checkbox)
        # Keep temporary files checkbox
        self.keep_temp_checkbox = QCheckBox("Keep &temporary files")
        self.keep_temp_checkbox.setChecked(False)
        self.keep_temp_checkbox.setToolTip("Do not delete intermediate files. Useful for debugging; uses extra disk space.")
        self.keep_temp_checkbox.toggled.connect(self._mark_dirty)
        form_layout.addRow("", self.keep_temp_checkbox)

        # Log file path with browse button
        log_file_layout = QHBoxLayout()
        log_file_layout.setContentsMargins(0, 0, 0, 0)
        self.log_file_edit = QLineEdit()
        self.log_file_edit.setPlaceholderText("Leave empty to log to console only")
        log_tooltip = "Optional path to write logs to a file. Leave empty to log to console only."
        self.log_file_edit.setToolTip(log_tooltip)
        self.log_file_edit._original_tooltip = log_tooltip
        self.log_file_edit.textChanged.connect(self._mark_dirty)
        self.browse_log_file_button = QToolButton()
        self.browse_log_file_button.setText("...")
        self.browse_log_file_button.setToolTip("Browse for log file location")
        self.browse_log_file_button.clicked.connect(self._on_browse_log_file)
        log_file_layout.addWidget(self.log_file_edit)
        log_file_layout.addWidget(self.browse_log_file_button)
        log_file_widget = QWidget()
        log_file_widget.setLayout(log_file_layout)
        form_layout.addRow("&Log file:", log_file_widget)
        # Export debug bundle button
        self.export_debug_button = QPushButton("E&xport debug bundle...")
        self.export_debug_button.setToolTip("Collect logs and diagnostic information into a bundle for support.")
        self.export_debug_button.clicked.connect(self._on_export_debug_clicked)
        form_layout.addRow("", self.export_debug_button)

        scroll.setWidget(content)

        # Set up tab layout
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)

        return tab

    def _connect_signals(self) -> None:
        """Connect widget signals to their handlers."""
        # Button box signals
        self.button_box.accepted.connect(self.onAccept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.onApply)
        self.button_box.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(self.onRestoreDefaults)

        # Connect validation signals for General tab
        if hasattr(self, "author_edit"):
            self.author_edit.textChanged.connect(lambda: self._validate_text_field(self.author_edit, "Author"))
            self.author_edit.textChanged.connect(self._update_dialog_buttons_enabled)
        if hasattr(self, "license_edit"):
            self.license_edit.textChanged.connect(lambda: self._validate_text_field(self.license_edit, "License"))
            self.license_edit.textChanged.connect(self._update_dialog_buttons_enabled)
        if hasattr(self, "pack_name_edit"):
            self.pack_name_edit.textChanged.connect(lambda: self._validate_text_field(self.pack_name_edit, "Pack name", 64))
            self.pack_name_edit.textChanged.connect(self._update_dialog_buttons_enabled)

        # Connect validation signals for Conversion tab
        if hasattr(self, "pages_edit"):
            self.pages_edit.textChanged.connect(self._validate_pages_field)
            self.pages_edit.textChanged.connect(self._update_dialog_buttons_enabled)

        # Connect validation signals for Debug tab
        if hasattr(self, "log_file_edit"):
            self.log_file_edit.textChanged.connect(lambda: self._validate_path_field(self.log_file_edit, "Log file"))
            self.log_file_edit.textChanged.connect(self._update_dialog_buttons_enabled)

        # Connect inter-widget dependency validation
        if hasattr(self, "picture_descriptions_checkbox"):
            self.picture_descriptions_checkbox.toggled.connect(self._on_picture_descriptions_toggled)
            self.picture_descriptions_checkbox.toggled.connect(self._update_dialog_buttons_enabled)

        # Connect preset control signals
        if hasattr(self, "preset_combo"):
            self.preset_combo.currentTextChanged.connect(self._on_preset_selection_changed)
        if hasattr(self, "new_preset_button"):
            self.new_preset_button.clicked.connect(self._on_new_preset_clicked)
        if hasattr(self, "save_preset_button"):
            self.save_preset_button.clicked.connect(self._on_save_preset_clicked)
        if hasattr(self, "delete_preset_button"):
            self.delete_preset_button.clicked.connect(self._on_delete_preset_clicked)

    def onAccept(self) -> None:
        """Handle OK button click."""
        if self.validateAll():
            self.saveSettings()
            self.accept()

    def onApply(self) -> None:
        """Handle Apply button click."""
        if self.validateAll():
            self.saveSettings()
            self._dirty = False
            self.button_box.button(QDialogButtonBox.StandardButton.Apply).setEnabled(False)

    def onRestoreDefaults(self) -> None:
        """Handle Restore Defaults button click."""
        # Reset all controls to their default values

        # General tab defaults
        if hasattr(self, "author_edit"):
            self.author_edit.setText("")
        if hasattr(self, "license_edit"):
            self.license_edit.setText("")
        if hasattr(self, "pack_name_edit"):
            self.pack_name_edit.setText("")
        if hasattr(self, "output_dir_selector"):
            # Default to user's Documents directory or current working directory
            default_output = str(Path.home() / "Documents")
            if not Path(default_output).exists():
                default_output = str(Path.cwd())
            self.output_dir_selector.set_path(default_output)
        if hasattr(self, "deterministic_ids_checkbox"):
            self.deterministic_ids_checkbox.setChecked(True)

        # Conversion tab defaults
        if hasattr(self, "toc_checkbox"):
            self.toc_checkbox.setChecked(True)
        if hasattr(self, "tables_combo"):
            self.tables_combo.setCurrentText("auto")
        if hasattr(self, "ocr_combo"):
            self.ocr_combo.setCurrentText("auto")
        if hasattr(self, "picture_descriptions_checkbox"):
            self.picture_descriptions_checkbox.setChecked(False)
            self._on_picture_descriptions_toggled(False)
        if hasattr(self, "vlm_repo_edit"):
            self.vlm_repo_edit.setText("")
        if hasattr(self, "pages_edit"):
            self.pages_edit.setText("")

        # Debug tab defaults
        if hasattr(self, "verbose_checkbox"):
            self.verbose_checkbox.setChecked(False)
        if hasattr(self, "log_level_combo"):
            self.log_level_combo.setCurrentText("INFO")
        if hasattr(self, "dry_run_checkbox"):
            self.dry_run_checkbox.setChecked(False)
        if hasattr(self, "keep_temp_checkbox"):
            self.keep_temp_checkbox.setChecked(False)
        if hasattr(self, "log_file_edit"):
            self.log_file_edit.setText("")

        # Reset export debug path
        self._export_debug_path = None

        # Mark as dirty and validate
        self._mark_dirty()

    def _create_preset_controls(self) -> QWidget:
        """Create the preset management controls."""
        widget = QWidget()
        widget.setAccessibleName("Preset controls")

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Preset label
        preset_label = QLabel("Preset:")
        preset_label.setAccessibleName("Preset selection label")
        layout.addWidget(preset_label)

        # Preset dropdown
        self.preset_combo = QComboBox()
        self.preset_combo.setAccessibleName("Preset selection")
        self.preset_combo.setToolTip("Select a configuration preset")
        self.preset_combo.setMinimumWidth(200)
        layout.addWidget(self.preset_combo)

        # New preset button
        self.new_preset_button = QPushButton("New...")
        self.new_preset_button.setAccessibleName("Create new preset")
        self.new_preset_button.setToolTip("Create a new preset from current settings")
        layout.addWidget(self.new_preset_button)

        # Save preset button
        self.save_preset_button = QPushButton("Save")
        self.save_preset_button.setAccessibleName("Save preset")
        self.save_preset_button.setToolTip("Save current settings to selected preset")
        self.save_preset_button.setEnabled(False)  # Disabled when no preset selected
        layout.addWidget(self.save_preset_button)

        # Delete preset button
        self.delete_preset_button = QPushButton("Delete")
        self.delete_preset_button.setAccessibleName("Delete preset")
        self.delete_preset_button.setToolTip("Delete the selected preset")
        self.delete_preset_button.setEnabled(False)  # Disabled when no preset selected
        layout.addWidget(self.delete_preset_button)

        # Add stretch to push buttons to the left
        layout.addStretch()

        return widget

    def loadSettings(self) -> None:
        """Load settings from persistent storage."""
        # Load configuration using ConfigManager
        config = self._config_manager.load_all()

        # Populate preset dropdown
        self._refresh_preset_list()

        # Select last used preset if available
        last_preset = self._config_manager.get_last_used_preset()
        if last_preset and last_preset in [self.preset_combo.itemText(i) for i in range(self.preset_combo.count())]:
            self.preset_combo.setCurrentText(last_preset)
        else:
            self.preset_combo.setCurrentIndex(-1)  # No selection

        # Load General tab settings
        if hasattr(self, "author_edit"):
            self.author_edit.setText(config.get("author", ""))
        if hasattr(self, "license_edit"):
            self.license_edit.setText(config.get("license", ""))
        if hasattr(self, "pack_name_edit"):
            self.pack_name_edit.setText(config.get("pack_name", ""))
        if hasattr(self, "output_dir_selector"):
            self.output_dir_selector.set_path(config.get("output_dir", ""))
        if hasattr(self, "deterministic_ids_checkbox"):
            self.deterministic_ids_checkbox.setChecked(config.get("deterministic_ids", True))

        # Load Conversion tab settings
        if hasattr(self, "toc_checkbox"):
            self.toc_checkbox.setChecked(config.get("toc", True))
        if hasattr(self, "tables_combo"):
            tables = config.get("tables", "auto")
            if tables in ["auto", "structured", "image-only"]:
                self.tables_combo.setCurrentText(tables)
        if hasattr(self, "ocr_combo"):
            ocr = config.get("ocr", "auto")
            if ocr in ["auto", "on", "off"]:
                self.ocr_combo.setCurrentText(ocr)
        if hasattr(self, "picture_descriptions_checkbox"):
            pic_desc = config.get("picture_descriptions", False)
            self.picture_descriptions_checkbox.setChecked(pic_desc)
            self._on_picture_descriptions_toggled(pic_desc)
        if hasattr(self, "vlm_repo_edit"):
            self.vlm_repo_edit.setText(config.get("vlm_repo", ""))
        if hasattr(self, "pages_edit"):
            self.pages_edit.setText(config.get("pages", ""))

        # Load Debug tab settings
        if hasattr(self, "verbose_checkbox"):
            self.verbose_checkbox.setChecked(config.get("verbose", False))
        if hasattr(self, "log_level_combo"):
            log_level = config.get("log_level", "INFO")
            if log_level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
                self.log_level_combo.setCurrentText(log_level)
        if hasattr(self, "dry_run_checkbox"):
            self.dry_run_checkbox.setChecked(config.get("dry_run", False))
        if hasattr(self, "keep_temp_checkbox"):
            self.keep_temp_checkbox.setChecked(config.get("keep_temp", False))
        if hasattr(self, "log_file_edit"):
            self.log_file_edit.setText(config.get("log_file", ""))

        # Load export debug path
        self._export_debug_path = config.get("export_debug_path") or None

        # Reset dirty state after loading (only if not initializing)
        if not self._initializing:
            self._dirty = False
            self.button_box.button(QDialogButtonBox.StandardButton.Apply).setEnabled(False)

        # Validate all loaded settings
        self.validateAll()

    def saveSettings(self) -> None:
        """Save settings to persistent storage."""
        # Only save valid settings
        if not self.validateAll():
            return

        # Collect current configuration
        config: dict[str, Any] = {}

        # Save General tab settings
        if hasattr(self, "author_edit"):
            config["author"] = self.author_edit.text().strip()
        if hasattr(self, "license_edit"):
            config["license"] = self.license_edit.text().strip()
        if hasattr(self, "pack_name_edit"):
            config["pack_name"] = self.pack_name_edit.text().strip()
        if hasattr(self, "output_dir_selector"):
            config["output_dir"] = self.output_dir_selector.path()
        if hasattr(self, "deterministic_ids_checkbox"):
            config["deterministic_ids"] = self.deterministic_ids_checkbox.isChecked()

        # Save Conversion tab settings
        if hasattr(self, "toc_checkbox"):
            config["toc"] = self.toc_checkbox.isChecked()
        if hasattr(self, "tables_combo"):
            config["tables"] = self.tables_combo.currentText()
        if hasattr(self, "ocr_combo"):
            config["ocr"] = self.ocr_combo.currentText()
        if hasattr(self, "picture_descriptions_checkbox"):
            config["picture_descriptions"] = self.picture_descriptions_checkbox.isChecked()
        if hasattr(self, "vlm_repo_edit"):
            config["vlm_repo"] = self.vlm_repo_edit.text().strip()
        if hasattr(self, "pages_edit"):
            config["pages"] = self.pages_edit.text().strip()

        # Save Debug tab settings
        if hasattr(self, "verbose_checkbox"):
            config["verbose"] = self.verbose_checkbox.isChecked()
        if hasattr(self, "log_level_combo"):
            config["log_level"] = self.log_level_combo.currentText()
        if hasattr(self, "dry_run_checkbox"):
            config["dry_run"] = self.dry_run_checkbox.isChecked()
        if hasattr(self, "keep_temp_checkbox"):
            config["keep_temp"] = self.keep_temp_checkbox.isChecked()
        if hasattr(self, "log_file_edit"):
            config["log_file"] = self.log_file_edit.text().strip()

        # Save export debug path
        if self._export_debug_path:
            config["export_debug_path"] = self._export_debug_path
        else:
            config["export_debug_path"] = ""

        # Import configuration to ConfigManager
        self._config_manager.import_config(config)

    def validateAll(self) -> bool:
        """Validate all input fields."""
        all_valid = True

        # Validate General tab fields
        if hasattr(self, "author_edit") and not self._validate_text_field(self.author_edit, "Author"):
            all_valid = False
        if hasattr(self, "license_edit") and not self._validate_text_field(self.license_edit, "License"):
            all_valid = False
        if hasattr(self, "pack_name_edit") and not self._validate_text_field(self.pack_name_edit, "Pack name", 64):
            all_valid = False

        # Validate output directory through the widget if it has validation
        if hasattr(self, "output_dir_selector"):
            path = self.output_dir_selector.path()
            if path and not self._is_dir_writable(path):
                # Note: We can't set error on the widget directly since it's a custom widget
                # The OutputDirectorySelector should handle its own validation
                all_valid = False

        # Validate Conversion tab fields
        if not self._validate_pages_field():
            all_valid = False

        # Validate VLM field dependency
        if (
            hasattr(self, "picture_descriptions_checkbox")
            and hasattr(self, "vlm_repo_edit")
            and self.picture_descriptions_checkbox.isChecked()
        ):
            vlm_text = self.vlm_repo_edit.text().strip()
            if not vlm_text:
                self._set_field_error(self.vlm_repo_edit, "VLM model is required when picture descriptions are enabled")
                all_valid = False
            else:
                self._clear_field_error(self.vlm_repo_edit)

        # Validate Debug tab fields
        if hasattr(self, "log_file_edit") and not self._validate_path_field(self.log_file_edit, "Log file"):
            all_valid = False

        return all_valid

    def toArgs(self) -> dict[str, str | bool | int]:
        """Convert current settings to CLI arguments dictionary."""
        args: dict[str, str | bool | int] = {}

        # Only include arguments if validation passes
        if not self.validateAll():
            return args

        # General tab arguments
        if hasattr(self, "author_edit"):
            author = self.author_edit.text().strip()
            if author:
                args["--author"] = author
        if hasattr(self, "license_edit"):
            license_text = self.license_edit.text().strip()
            if license_text:
                args["--license"] = license_text
        if hasattr(self, "pack_name_edit"):
            pack_name = self.pack_name_edit.text().strip()
            if pack_name:
                args["--pack-name"] = pack_name
        if hasattr(self, "output_dir_selector"):
            output_path = self.output_dir_selector.path()
            if output_path:
                args["--out-dir"] = output_path
        if hasattr(self, "deterministic_ids_checkbox"):
            if self.deterministic_ids_checkbox.isChecked():
                args["--deterministic-ids"] = True
            else:
                args["--no-deterministic-ids"] = True

        # Conversion tab arguments
        if hasattr(self, "toc_checkbox"):
            if self.toc_checkbox.isChecked():
                args["--toc"] = True
            else:
                args["--no-toc"] = True
        if hasattr(self, "tables_combo"):
            tables_value = self.tables_combo.currentText()
            if tables_value != "auto":  # Only include non-default values
                args["--tables"] = tables_value
        if hasattr(self, "ocr_combo"):
            ocr_value = self.ocr_combo.currentText()
            if ocr_value != "auto":  # Only include non-default values
                args["--ocr"] = ocr_value
        if hasattr(self, "picture_descriptions_checkbox"):
            if self.picture_descriptions_checkbox.isChecked():
                args["--picture-descriptions"] = "on"
            else:
                args["--picture-descriptions"] = "off"
        if hasattr(self, "vlm_repo_edit"):
            vlm_repo = self.vlm_repo_edit.text().strip()
            if vlm_repo:
                args["--vlm-repo-id"] = vlm_repo
        if hasattr(self, "pages_edit"):
            pages_spec = self.pages_edit.text().strip()
            if pages_spec:
                # Validate and normalize the pages specification
                ranges = self._parse_pages(pages_spec)
                if ranges is not None:
                    # Convert back to normalized string format
                    normalized_parts = []
                    for start, end in ranges:
                        if start == end:
                            normalized_parts.append(str(start))
                        else:
                            normalized_parts.append(f"{start}-{end}")
                    args["--pages"] = ",".join(normalized_parts)

        # Debug tab arguments
        if hasattr(self, "verbose_checkbox") and self.verbose_checkbox.isChecked():
            args["--verbose"] = True
        if hasattr(self, "log_level_combo"):
            log_level = self.log_level_combo.currentText()
            if log_level != "INFO":  # Only include non-default values
                args["--log-level"] = log_level
        if hasattr(self, "dry_run_checkbox") and self.dry_run_checkbox.isChecked():
            args["--dry-run"] = True
        if hasattr(self, "keep_temp_checkbox") and self.keep_temp_checkbox.isChecked():
            args["--keep-temp"] = True
        if hasattr(self, "log_file_edit"):
            log_file = self.log_file_edit.text().strip()
            if log_file:
                args["--log-file"] = log_file
        if hasattr(self, "_export_debug_path") and self._export_debug_path:
            args["--export-debug"] = self._export_debug_path

        return args

    def fromArgs(self, args: dict[str, str | bool | int] | list[str]) -> None:
        """Populate UI from CLI arguments dictionary or list."""
        # Convert list format to dictionary if needed
        if isinstance(args, list):
            args = self._parse_args_list(args)

        # General tab arguments
        if hasattr(self, "author_edit") and "--author" in args:
            self.author_edit.setText(str(args["--author"]))
        if hasattr(self, "license_edit") and "--license" in args:
            self.license_edit.setText(str(args["--license"]))
        if hasattr(self, "pack_name_edit") and "--pack-name" in args:
            self.pack_name_edit.setText(str(args["--pack-name"]))
        if hasattr(self, "output_dir_selector") and "--out-dir" in args:
            self.output_dir_selector.set_path(str(args["--out-dir"]))
        if hasattr(self, "deterministic_ids_checkbox"):
            if "--deterministic-ids" in args:
                self.deterministic_ids_checkbox.setChecked(bool(args["--deterministic-ids"]))
            elif "--no-deterministic-ids" in args:
                self.deterministic_ids_checkbox.setChecked(not bool(args["--no-deterministic-ids"]))

        # Conversion tab arguments
        if hasattr(self, "toc_checkbox"):
            if "--toc" in args:
                self.toc_checkbox.setChecked(bool(args["--toc"]))
            elif "--no-toc" in args:
                self.toc_checkbox.setChecked(not bool(args["--no-toc"]))
        if hasattr(self, "tables_combo") and "--tables" in args:
            tables_value = str(args["--tables"])
            if tables_value in ["auto", "structured", "image-only"]:
                self.tables_combo.setCurrentText(tables_value)
        if hasattr(self, "ocr_combo") and "--ocr" in args:
            ocr_value = str(args["--ocr"])
            if ocr_value in ["auto", "on", "off"]:
                self.ocr_combo.setCurrentText(ocr_value)
        if hasattr(self, "picture_descriptions_checkbox") and "--picture-descriptions" in args:
            pic_desc_value = str(args["--picture-descriptions"])
            self.picture_descriptions_checkbox.setChecked(pic_desc_value == "on")
            self._on_picture_descriptions_toggled(pic_desc_value == "on")
        if hasattr(self, "vlm_repo_edit") and "--vlm-repo-id" in args:
            self.vlm_repo_edit.setText(str(args["--vlm-repo-id"]))
        if hasattr(self, "pages_edit") and "--pages" in args:
            pages_value = str(args["--pages"])
            # Normalize the pages specification
            ranges = self._parse_pages(pages_value)
            if ranges is not None:
                # Convert back to normalized string format
                normalized_parts = []
                for start, end in ranges:
                    if start == end:
                        normalized_parts.append(str(start))
                    else:
                        normalized_parts.append(f"{start}-{end}")
                self.pages_edit.setText(",".join(normalized_parts))
            else:
                # Keep original if parsing fails
                self.pages_edit.setText(pages_value)

        # Debug tab arguments
        if hasattr(self, "verbose_checkbox") and "--verbose" in args:
            self.verbose_checkbox.setChecked(bool(args["--verbose"]))
        if hasattr(self, "log_level_combo") and "--log-level" in args:
            log_level = str(args["--log-level"])
            if log_level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
                self.log_level_combo.setCurrentText(log_level)
        if hasattr(self, "dry_run_checkbox") and "--dry-run" in args:
            self.dry_run_checkbox.setChecked(bool(args["--dry-run"]))
        if hasattr(self, "keep_temp_checkbox") and "--keep-temp" in args:
            self.keep_temp_checkbox.setChecked(bool(args["--keep-temp"]))
        if hasattr(self, "log_file_edit") and "--log-file" in args:
            self.log_file_edit.setText(str(args["--log-file"]))
        if "--export-debug" in args:
            self._export_debug_path = str(args["--export-debug"]) if args["--export-debug"] else None

        # Reset dirty state after loading from args (only if not initializing)
        if not self._initializing:
            self._dirty = False
            self.button_box.button(QDialogButtonBox.StandardButton.Apply).setEnabled(False)

        # Validate all loaded settings
        self.validateAll()

    def _parse_args_list(self, args_list: list[str]) -> dict[str, str | bool | int]:
        """Parse a list of CLI arguments into a dictionary."""
        args_dict: dict[str, str | bool | int] = {}
        i = 0
        while i < len(args_list):
            arg = args_list[i]

            # Handle --key=value format
            if "=" in arg:
                key, value = arg.split("=", 1)
                args_dict[key] = value
                i += 1
            # Handle boolean flags
            elif arg.startswith("--") and (i + 1 >= len(args_list) or args_list[i + 1].startswith("--")):
                args_dict[arg] = True
                i += 1
            # Handle --key value format
            elif arg.startswith("--") and i + 1 < len(args_list):
                key = arg
                value = args_list[i + 1]
                args_dict[key] = value
                i += 2
            else:
                i += 1

        return args_dict

    def _refresh_preset_list(self) -> None:
        """Refresh the preset dropdown with available presets."""
        current_selection = self.preset_combo.currentText()

        self.preset_combo.clear()
        self.preset_combo.addItem("(No preset selected)", "")

        try:
            presets = self._preset_manager.list_presets()
            for preset_name in presets:
                self.preset_combo.addItem(preset_name, preset_name)
        except Exception as e:
            logger.error(f"Failed to load presets: {e}")
            QMessageBox.warning(self, "Preset Error", f"Failed to load presets: {e}")

        # Restore selection if it still exists
        if current_selection:
            index = self.preset_combo.findText(current_selection)
            if index >= 0:
                self.preset_combo.setCurrentIndex(index)

        # Update button states
        self._update_preset_button_states()

    def _update_preset_button_states(self) -> None:
        """Update the enabled state of preset buttons based on current selection."""
        has_selection = self.preset_combo.currentIndex() > 0
        self.save_preset_button.setEnabled(has_selection)
        self.delete_preset_button.setEnabled(has_selection)

    def _on_preset_selection_changed(self) -> None:
        """Handle preset selection change."""
        if self._initializing:
            return

        current_preset = self.preset_combo.currentData()

        if current_preset:
            # Load the selected preset
            try:
                config = self._preset_manager.load_preset(current_preset)
                self._config_manager.import_config(config)

                # Reload UI with new configuration
                self._initializing = True  # Prevent marking as dirty
                self.loadSettings()
                self._initializing = False

                # Update last used preset
                self._config_manager.set_last_used_preset(current_preset)

                logger.info(f"Loaded preset: {current_preset}")

            except PresetError as e:
                logger.error(f"Failed to load preset '{current_preset}': {e}")
                QMessageBox.warning(self, "Preset Error", f"Failed to load preset '{current_preset}': {e}")
                self.preset_combo.setCurrentIndex(0)  # Reset to no selection
        else:
            # Clear last used preset
            self._config_manager.set_last_used_preset(None)

        self._update_preset_button_states()

    def _on_new_preset_clicked(self) -> None:
        """Handle New preset button click."""
        name, ok = QInputDialog.getText(self, "New Preset", "Enter preset name:", text="My Preset")

        if not ok or not name.strip():
            return

        name = name.strip()

        # Check if preset already exists
        if self._preset_manager.preset_exists(name):
            reply = QMessageBox.question(
                self,
                "Preset Exists",
                f"Preset '{name}' already exists. Overwrite?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        try:
            # Get current configuration
            current_config = self._get_current_config()

            # Save preset
            self._preset_manager.save_preset(name, current_config, overwrite=True)

            # Refresh list and select new preset
            self._refresh_preset_list()
            self.preset_combo.setCurrentText(name)

            # Update last used preset
            self._config_manager.set_last_used_preset(name)

            logger.info(f"Created preset: {name}")

        except PresetError as e:
            logger.error(f"Failed to create preset '{name}': {e}")
            QMessageBox.warning(self, "Preset Error", f"Failed to create preset '{name}': {e}")

    def _on_save_preset_clicked(self) -> None:
        """Handle Save preset button click."""
        current_preset = self.preset_combo.currentData()
        if not current_preset:
            return

        reply = QMessageBox.question(
            self,
            "Save Preset",
            f"Save current settings to preset '{current_preset}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            # Get current configuration
            current_config = self._get_current_config()

            # Save preset
            self._preset_manager.save_preset(current_preset, current_config, overwrite=True)

            logger.info(f"Saved preset: {current_preset}")

        except PresetError as e:
            logger.error(f"Failed to save preset '{current_preset}': {e}")
            QMessageBox.warning(self, "Preset Error", f"Failed to save preset '{current_preset}': {e}")

    def _on_delete_preset_clicked(self) -> None:
        """Handle Delete preset button click."""
        current_preset = self.preset_combo.currentData()
        if not current_preset:
            return

        reply = QMessageBox.question(
            self,
            "Delete Preset",
            f"Delete preset '{current_preset}'? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            # Delete preset
            self._preset_manager.delete_preset(current_preset)

            # Refresh list and clear selection
            self._refresh_preset_list()
            self.preset_combo.setCurrentIndex(0)  # No selection

            # Clear last used preset if it was this one
            if self._config_manager.get_last_used_preset() == current_preset:
                self._config_manager.set_last_used_preset(None)

            logger.info(f"Deleted preset: {current_preset}")

        except PresetError as e:
            logger.error(f"Failed to delete preset '{current_preset}': {e}")
            QMessageBox.warning(self, "Preset Error", f"Failed to delete preset '{current_preset}': {e}")

    def _get_current_config(self) -> dict[str, Any]:
        """Get the current configuration from UI controls."""
        config: dict[str, Any] = {}

        # General tab settings
        if hasattr(self, "author_edit"):
            config["author"] = self.author_edit.text().strip()
        if hasattr(self, "license_edit"):
            config["license"] = self.license_edit.text().strip()
        if hasattr(self, "pack_name_edit"):
            config["pack_name"] = self.pack_name_edit.text().strip()
        if hasattr(self, "output_dir_selector"):
            config["output_dir"] = self.output_dir_selector.path()
        if hasattr(self, "deterministic_ids_checkbox"):
            config["deterministic_ids"] = self.deterministic_ids_checkbox.isChecked()

        # Conversion tab settings
        if hasattr(self, "toc_checkbox"):
            config["toc"] = self.toc_checkbox.isChecked()
        if hasattr(self, "tables_combo"):
            config["tables"] = self.tables_combo.currentText()
        if hasattr(self, "ocr_combo"):
            config["ocr"] = self.ocr_combo.currentText()
        if hasattr(self, "picture_descriptions_checkbox"):
            config["picture_descriptions"] = self.picture_descriptions_checkbox.isChecked()
        if hasattr(self, "vlm_repo_edit"):
            config["vlm_repo"] = self.vlm_repo_edit.text().strip()
        if hasattr(self, "pages_edit"):
            config["pages"] = self.pages_edit.text().strip()

        # Debug tab settings
        if hasattr(self, "verbose_checkbox"):
            config["verbose"] = self.verbose_checkbox.isChecked()
        if hasattr(self, "log_level_combo"):
            config["log_level"] = self.log_level_combo.currentText()
        if hasattr(self, "dry_run_checkbox"):
            config["dry_run"] = self.dry_run_checkbox.isChecked()
        if hasattr(self, "keep_temp_checkbox"):
            config["keep_temp"] = self.keep_temp_checkbox.isChecked()
        if hasattr(self, "log_file_edit"):
            config["log_file"] = self.log_file_edit.text().strip()

        # Export debug path
        if self._export_debug_path:
            config["export_debug_path"] = self._export_debug_path
        else:
            config["export_debug_path"] = ""

        return config

    def _mark_dirty(self) -> None:
        """Mark settings as modified and enable Apply button."""
        # Don't mark dirty during initialization
        if self._initializing:
            return

        if not self._dirty:
            self._dirty = True
            # Update button states based on validation
            self._update_dialog_buttons_enabled()

    def _on_picture_descriptions_toggled(self, checked: bool) -> None:
        """Handle picture descriptions checkbox toggle to enable/disable VLM repo field."""
        if hasattr(self, "vlm_repo_edit"):
            self.vlm_repo_edit.setEnabled(checked)

    def _on_browse_log_file(self) -> None:
        """Handle browse button click for log file selection."""
        file_path, _ = QFileDialog.getSaveFileName(self, "Select Log File", "", "Log Files (*.log *.txt);;All Files (*)")
        if file_path:
            self.log_file_edit.setText(file_path)
            self._mark_dirty()

    def _on_export_debug_clicked(self) -> None:
        """Handle export debug bundle button click."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Debug Bundle", "debug-bundle.zip", "ZIP Files (*.zip);;All Files (*)"
        )
        if file_path:
            self._export_debug_path = file_path
            self._mark_dirty()
