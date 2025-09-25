"""
Settings dialog for the PDF2Foundry GUI application.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from gui.widgets.directory_selector import OutputDirectorySelector


class SettingsDialog(QDialog):
    """
    Settings dialog with tabbed interface for PDF2Foundry CLI options.

    Provides organized access to all CLI options through General, Conversion,
    and Debug tabs with proper validation and persistence.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # State tracking
        self._dirty = False

        # Set up the dialog
        self._setup_dialog()

        # Create the UI
        self._setup_ui()

        # Connect signals
        self._connect_signals()

        # Load settings
        self.loadSettings()

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
        self.author_edit.textChanged.connect(self._mark_dirty)
        form_layout.addRow("&Author:", self.author_edit)

        # License field
        self.license_edit = QLineEdit()
        self.license_edit.setPlaceholderText("Enter license...")
        self.license_edit.setToolTip("License string for module.json.")
        self.license_edit.textChanged.connect(self._mark_dirty)
        form_layout.addRow("&License:", self.license_edit)

        # Pack name field
        self.pack_name_edit = QLineEdit()
        self.pack_name_edit.setPlaceholderText("Will default to <mod-id>-journals")
        self.pack_name_edit.setToolTip("Compendium pack name.")
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
        self.pages_edit.setToolTip(
            "Page list/ranges to process. Format: comma-separated list of " "page numbers and ranges (e.g., '1,5-10,15')."
        )
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

        # Placeholder for actual controls (will be implemented in subtask 4.4)
        placeholder = QLabel("Debug settings will be implemented here")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #666; font-style: italic; padding: 20px;")
        form_layout.addRow(placeholder)

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

    def loadSettings(self) -> None:
        """Load settings from persistent storage."""
        # Stub implementation - will be implemented in subtask 4.5
        pass

    def saveSettings(self) -> None:
        """Save settings to persistent storage."""
        # Stub implementation - will be implemented in subtask 4.5
        pass

    def validateAll(self) -> bool:
        """Validate all input fields."""
        # Stub implementation - will be implemented in subtask 4.5
        return True

    def toArgs(self) -> dict[str, str | bool | int]:
        """Convert current settings to CLI arguments dictionary."""
        args: dict[str, str | bool | int] = {}

        # General tab arguments
        if hasattr(self, "author_edit") and self.author_edit.text().strip():
            args["--author"] = self.author_edit.text().strip()

        if hasattr(self, "license_edit") and self.license_edit.text().strip():
            args["--license"] = self.license_edit.text().strip()

        if hasattr(self, "pack_name_edit") and self.pack_name_edit.text().strip():
            args["--pack-name"] = self.pack_name_edit.text().strip()

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
            if tables_value != "auto":  # Only include if not default
                args["--tables"] = tables_value

        if hasattr(self, "ocr_combo"):
            ocr_value = self.ocr_combo.currentText()
            if ocr_value != "auto":  # Only include if not default
                args["--ocr"] = ocr_value

        if hasattr(self, "picture_descriptions_checkbox"):
            if self.picture_descriptions_checkbox.isChecked():
                args["--picture-descriptions"] = "on"
            else:
                args["--picture-descriptions"] = "off"

        if hasattr(self, "vlm_repo_edit") and self.vlm_repo_edit.text().strip():
            args["--vlm-repo-id"] = self.vlm_repo_edit.text().strip()

        if hasattr(self, "pages_edit") and self.pages_edit.text().strip():
            args["--pages"] = self.pages_edit.text().strip()

        return args

    def fromArgs(self, args: dict[str, str | bool | int]) -> None:
        """Populate UI from CLI arguments dictionary."""
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
            # Trigger the toggle handler to enable/disable VLM field
            self._on_picture_descriptions_toggled(pic_desc_value == "on")

        if hasattr(self, "vlm_repo_edit") and "--vlm-repo-id" in args:
            self.vlm_repo_edit.setText(str(args["--vlm-repo-id"]))

        if hasattr(self, "pages_edit") and "--pages" in args:
            self.pages_edit.setText(str(args["--pages"]))

    def _mark_dirty(self) -> None:
        """Mark settings as modified and enable Apply button."""
        if not self._dirty:
            self._dirty = True
            self.button_box.button(QDialogButtonBox.StandardButton.Apply).setEnabled(True)

    def _on_picture_descriptions_toggled(self, checked: bool) -> None:
        """Handle picture descriptions checkbox toggle to enable/disable VLM repo field."""
        if hasattr(self, "vlm_repo_edit"):
            self.vlm_repo_edit.setEnabled(checked)
