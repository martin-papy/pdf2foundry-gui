"""
Tests for the SettingsDialog widget.
"""

from PySide6.QtWidgets import QDialogButtonBox

from gui.dialogs import SettingsDialog


class TestSettingsDialog:
    """Test cases for SettingsDialog functionality."""

    def test_dialog_creation(self, qtbot):
        """Test that SettingsDialog can be instantiated."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        assert dialog is not None
        assert dialog.windowTitle() == "PDF2Foundry Settings"
        assert dialog.isModal()

    def test_dialog_has_three_tabs(self, qtbot):
        """Test that dialog has General, Conversion, and Debug tabs."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Check tab count
        assert dialog.tab_widget.count() == 3

        # Check tab names
        assert dialog.tab_widget.tabText(0) == "General"
        assert dialog.tab_widget.tabText(1) == "Conversion"
        assert dialog.tab_widget.tabText(2) == "Debug"

    def test_tabs_are_navigable(self, qtbot):
        """Test that tabs can be navigated with keyboard."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Start on first tab
        assert dialog.tab_widget.currentIndex() == 0

        # Navigate to second tab
        dialog.tab_widget.setCurrentIndex(1)
        assert dialog.tab_widget.currentIndex() == 1

        # Navigate to third tab
        dialog.tab_widget.setCurrentIndex(2)
        assert dialog.tab_widget.currentIndex() == 2

    def test_button_box_exists(self, qtbot):
        """Test that dialog has OK, Cancel, and Apply buttons."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Check button box exists
        assert dialog.button_box is not None

        # Check buttons exist
        ok_button = dialog.button_box.button(QDialogButtonBox.StandardButton.Ok)
        cancel_button = dialog.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        apply_button = dialog.button_box.button(QDialogButtonBox.StandardButton.Apply)

        assert ok_button is not None
        assert cancel_button is not None
        assert apply_button is not None

        # Apply should be initially disabled
        assert not apply_button.isEnabled()

    def test_button_signals_connected(self, qtbot):
        """Test that button signals are properly connected."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Test that buttons emit expected signals
        with qtbot.waitSignal(dialog.accepted, timeout=1000):
            dialog.button_box.accepted.emit()

        with qtbot.waitSignal(dialog.rejected, timeout=1000):
            dialog.button_box.rejected.emit()

    def test_dialog_size_and_modality(self, qtbot):
        """Test dialog size and modality settings."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Check size
        assert dialog.size().width() == 600
        assert dialog.size().height() == 500
        assert dialog.minimumSize().width() == 500
        assert dialog.minimumSize().height() == 400

        # Check modality
        assert dialog.isModal()

    def test_accessibility_properties(self, qtbot):
        """Test that accessibility properties are set correctly."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Check tab widget accessibility
        assert dialog.tab_widget.accessibleName() == "Settings tabs"

        # Check button box accessibility
        assert dialog.button_box.accessibleName() == "Dialog buttons"

        # Check tab accessibility
        assert dialog.general_tab.accessibleName() == "General settings"
        assert dialog.conversion_tab.accessibleName() == "Conversion settings"
        assert dialog.debug_tab.accessibleName() == "Debug settings"

    def test_stub_methods_exist(self, qtbot):
        """Test that all required stub methods exist and are callable."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Test stub methods don't raise exceptions
        dialog.loadSettings()
        dialog.saveSettings()
        assert dialog.validateAll() is True
        # toArgs() returns default values from initialized controls, not empty dict
        args = dialog.toArgs()
        assert isinstance(args, dict)
        # Should contain at least the default values
        assert "--deterministic-ids" in args or "--no-deterministic-ids" in args
        assert "--toc" in args or "--no-toc" in args
        dialog.fromArgs({})

        # Test dirty state management
        assert not dialog._dirty
        dialog._mark_dirty()
        assert dialog._dirty

        # Apply button should be enabled after marking dirty
        apply_button = dialog.button_box.button(QDialogButtonBox.StandardButton.Apply)
        assert apply_button.isEnabled()

    def test_tab_content_placeholders(self, qtbot):
        """Test that tabs contain placeholder content."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Each tab should have a scroll area with placeholder content
        # This is a basic check that the tab structure is correct
        assert dialog.general_tab.layout() is not None
        assert dialog.conversion_tab.layout() is not None
        assert dialog.debug_tab.layout() is not None

    def test_general_tab_controls_exist(self, qtbot):
        """Test that General tab contains all expected controls."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Check that all General tab controls exist
        assert hasattr(dialog, "author_edit")
        assert hasattr(dialog, "license_edit")
        assert hasattr(dialog, "pack_name_edit")
        assert hasattr(dialog, "output_dir_selector")
        assert hasattr(dialog, "deterministic_ids_checkbox")

        # Check initial states
        assert dialog.author_edit.text() == ""
        assert dialog.license_edit.text() == ""
        assert dialog.pack_name_edit.text() == ""
        assert dialog.deterministic_ids_checkbox.isChecked()  # Default ON

    def test_general_tab_tooltips(self, qtbot):
        """Test that General tab controls have proper tooltips."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        assert dialog.author_edit.toolTip() == "Author metadata for module.json."
        assert dialog.license_edit.toolTip() == "License string for module.json."
        assert dialog.pack_name_edit.toolTip() == "Compendium pack name."
        assert dialog.output_dir_selector.toolTip() == "Where the module will be written."
        assert dialog.deterministic_ids_checkbox.toolTip() == "Stable SHA1-based IDs to keep links consistent."

    def test_general_tab_dirty_state_tracking(self, qtbot):
        """Test that changing General tab controls marks dialog as dirty."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        apply_button = dialog.button_box.button(dialog.button_box.StandardButton.Apply)

        # Initially not dirty
        assert not dialog._dirty
        assert not apply_button.isEnabled()

        # Change author field
        dialog.author_edit.setText("Test Author")
        assert dialog._dirty
        assert apply_button.isEnabled()

        # Reset dirty state
        dialog._dirty = False
        apply_button.setEnabled(False)

        # Change license field
        dialog.license_edit.setText("MIT")
        assert dialog._dirty
        assert apply_button.isEnabled()

        # Reset dirty state
        dialog._dirty = False
        apply_button.setEnabled(False)

        # Change pack name field
        dialog.pack_name_edit.setText("custom-pack")
        assert dialog._dirty
        assert apply_button.isEnabled()

        # Reset dirty state
        dialog._dirty = False
        apply_button.setEnabled(False)

        # Change deterministic IDs checkbox
        dialog.deterministic_ids_checkbox.setChecked(False)
        assert dialog._dirty
        assert apply_button.isEnabled()

    def test_general_tab_to_args_mapping(self, qtbot):
        """Test that General tab controls map correctly to CLI arguments."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Set some values
        dialog.author_edit.setText("Test Author")
        dialog.license_edit.setText("MIT License")
        dialog.pack_name_edit.setText("custom-pack")
        dialog.deterministic_ids_checkbox.setChecked(False)

        # Get CLI arguments
        args = dialog.toArgs()

        # Check mappings
        assert args["--author"] == "Test Author"
        assert args["--license"] == "MIT License"
        assert args["--pack-name"] == "custom-pack"
        assert args["--no-deterministic-ids"] is True
        assert "--deterministic-ids" not in args

    def test_general_tab_from_args_mapping(self, qtbot):
        """Test that CLI arguments populate General tab controls correctly."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Set CLI arguments
        args = {
            "--author": "John Doe",
            "--license": "GPL-3.0",
            "--pack-name": "my-journals",
            "--out-dir": "/tmp/output",
            "--no-deterministic-ids": True,
        }

        dialog.fromArgs(args)

        # Check that controls are populated
        assert dialog.author_edit.text() == "John Doe"
        assert dialog.license_edit.text() == "GPL-3.0"
        assert dialog.pack_name_edit.text() == "my-journals"
        assert not dialog.deterministic_ids_checkbox.isChecked()

    def test_general_tab_empty_values_not_in_args(self, qtbot):
        """Test that empty values are not included in CLI arguments."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Leave fields empty
        dialog.author_edit.setText("")
        dialog.license_edit.setText("   ")  # Whitespace only
        dialog.pack_name_edit.setText("")

        args = dialog.toArgs()

        # Empty/whitespace values should not be in args
        assert "--author" not in args
        assert "--license" not in args
        assert "--pack-name" not in args

    def test_conversion_tab_controls_exist(self, qtbot):
        """Test that Conversion tab contains all expected controls."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Check that all Conversion tab controls exist
        assert hasattr(dialog, "toc_checkbox")
        assert hasattr(dialog, "tables_combo")
        assert hasattr(dialog, "ocr_combo")
        assert hasattr(dialog, "picture_descriptions_checkbox")
        assert hasattr(dialog, "vlm_repo_edit")
        assert hasattr(dialog, "pages_edit")

        # Check initial states
        assert dialog.toc_checkbox.isChecked()  # Default ON
        assert dialog.tables_combo.currentText() == "auto"  # Default
        assert dialog.ocr_combo.currentText() == "auto"  # Default
        assert not dialog.picture_descriptions_checkbox.isChecked()  # Default OFF
        assert not dialog.vlm_repo_edit.isEnabled()  # Disabled when picture descriptions OFF
        assert dialog.pages_edit.text() == ""

    def test_conversion_tab_tooltips(self, qtbot):
        """Test that Conversion tab controls have proper tooltips."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        assert "Table of Contents" in dialog.toc_checkbox.toolTip()
        assert "handle tables" in dialog.tables_combo.toolTip()
        assert "OCR" in dialog.ocr_combo.toolTip()
        assert "AI captions" in dialog.picture_descriptions_checkbox.toolTip()
        assert "Hugging Face" in dialog.vlm_repo_edit.toolTip()
        assert "Page list" in dialog.pages_edit.toolTip()

    def test_picture_descriptions_vlm_dependency(self, qtbot):
        """Test that VLM field is enabled/disabled based on picture descriptions checkbox."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Initially disabled
        assert not dialog.vlm_repo_edit.isEnabled()

        # Enable picture descriptions
        dialog.picture_descriptions_checkbox.setChecked(True)
        assert dialog.vlm_repo_edit.isEnabled()

        # Disable picture descriptions
        dialog.picture_descriptions_checkbox.setChecked(False)
        assert not dialog.vlm_repo_edit.isEnabled()

    def test_conversion_tab_to_args_mapping(self, qtbot):
        """Test that Conversion tab controls map correctly to CLI arguments."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Set some values
        dialog.toc_checkbox.setChecked(False)
        dialog.tables_combo.setCurrentText("structured")
        dialog.ocr_combo.setCurrentText("on")
        dialog.picture_descriptions_checkbox.setChecked(True)
        dialog.vlm_repo_edit.setText("microsoft/Florence-2-base")
        dialog.pages_edit.setText("1,5-10,15")

        # Get CLI arguments
        args = dialog.toArgs()

        # Check mappings
        assert args["--no-toc"] is True
        assert "--toc" not in args
        assert args["--tables"] == "structured"
        assert args["--ocr"] == "on"
        assert args["--picture-descriptions"] == "on"
        assert args["--vlm-repo-id"] == "microsoft/Florence-2-base"
        assert args["--pages"] == "1,5-10,15"

    def test_conversion_tab_default_values_not_in_args(self, qtbot):
        """Test that default values are not included in CLI arguments."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Keep defaults: toc=True, tables=auto, ocr=auto, picture-descriptions=False
        args = dialog.toArgs()

        # Default values should be included for boolean flags but not for enums
        assert args["--toc"] is True  # Default but still included
        assert "--tables" not in args  # Default "auto" not included
        assert "--ocr" not in args  # Default "auto" not included
        assert args["--picture-descriptions"] == "off"  # Default but still included

    def test_conversion_tab_from_args_mapping(self, qtbot):
        """Test that CLI arguments populate Conversion tab controls correctly."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Set CLI arguments
        args = {
            "--no-toc": True,
            "--tables": "image-only",
            "--ocr": "off",
            "--picture-descriptions": "on",
            "--vlm-repo-id": "Salesforce/blip-image-captioning-base",
            "--pages": "2,4-8",
        }

        dialog.fromArgs(args)

        # Check that controls are populated
        assert not dialog.toc_checkbox.isChecked()
        assert dialog.tables_combo.currentText() == "image-only"
        assert dialog.ocr_combo.currentText() == "off"
        assert dialog.picture_descriptions_checkbox.isChecked()
        assert dialog.vlm_repo_edit.isEnabled()  # Should be enabled when picture descriptions is on
        assert dialog.vlm_repo_edit.text() == "Salesforce/blip-image-captioning-base"
        assert dialog.pages_edit.text() == "2,4-8"

    def test_conversion_tab_dirty_state_tracking(self, qtbot):
        """Test that changing Conversion tab controls marks dialog as dirty."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        apply_button = dialog.button_box.button(dialog.button_box.StandardButton.Apply)

        # Initially not dirty
        assert not dialog._dirty
        assert not apply_button.isEnabled()

        # Test each control
        controls_to_test = [
            (dialog.toc_checkbox, lambda: dialog.toc_checkbox.setChecked(False)),
            (dialog.tables_combo, lambda: dialog.tables_combo.setCurrentText("structured")),
            (dialog.ocr_combo, lambda: dialog.ocr_combo.setCurrentText("on")),
            (dialog.picture_descriptions_checkbox, lambda: dialog.picture_descriptions_checkbox.setChecked(True)),
            (dialog.vlm_repo_edit, lambda: dialog.vlm_repo_edit.setText("test-model")),
            (dialog.pages_edit, lambda: dialog.pages_edit.setText("1,2,3")),
        ]

        for control, action in controls_to_test:
            # Reset dirty state
            dialog._dirty = False
            apply_button.setEnabled(False)

            # Change the control
            action()

            # Should be dirty now
            assert dialog._dirty, f"Control {control} did not mark dialog as dirty"
            assert apply_button.isEnabled(), f"Control {control} did not enable Apply button"
