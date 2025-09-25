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
        assert dialog.tab_widget.count() == 3
        assert dialog.tab_widget.tabText(0) == "General"
        assert dialog.tab_widget.tabText(1) == "Conversion"
        assert dialog.tab_widget.tabText(2) == "Debug"

    def test_tabs_are_navigable(self, qtbot):
        """Test that tabs can be navigated with keyboard."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)
        assert dialog.tab_widget.currentIndex() == 0
        dialog.tab_widget.setCurrentIndex(1)
        assert dialog.tab_widget.currentIndex() == 1
        dialog.tab_widget.setCurrentIndex(2)
        assert dialog.tab_widget.currentIndex() == 2

    def test_button_box_exists(self, qtbot):
        """Test that dialog has OK, Cancel, and Apply buttons."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)
        assert dialog.button_box is not None
        ok_button = dialog.button_box.button(QDialogButtonBox.StandardButton.Ok)
        cancel_button = dialog.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        apply_button = dialog.button_box.button(QDialogButtonBox.StandardButton.Apply)
        assert ok_button is not None
        assert cancel_button is not None
        assert apply_button is not None
        assert not apply_button.isEnabled()

    def test_button_signals_connected(self, qtbot):
        """Test that button signals are properly connected."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)
        with qtbot.waitSignal(dialog.accepted, timeout=1000):
            dialog.button_box.accepted.emit()
        with qtbot.waitSignal(dialog.rejected, timeout=1000):
            dialog.button_box.rejected.emit()

    def test_dialog_size_and_modality(self, qtbot):
        """Test dialog size and modality settings."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)
        assert dialog.size().width() == 600
        assert dialog.size().height() == 500
        assert dialog.minimumSize().width() == 500
        assert dialog.minimumSize().height() == 400
        assert dialog.isModal()

    def test_accessibility_properties(self, qtbot):
        """Test that accessibility properties are set correctly."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)
        assert dialog.tab_widget.accessibleName() == "Settings tabs"
        assert dialog.button_box.accessibleName() == "Dialog buttons"
        assert dialog.general_tab.accessibleName() == "General settings"
        assert dialog.conversion_tab.accessibleName() == "Conversion settings"
        assert dialog.debug_tab.accessibleName() == "Debug settings"

    def test_stub_methods_exist(self, qtbot):
        """Test that all required stub methods exist and are callable."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)
        dialog.loadSettings()
        dialog.saveSettings()
        assert dialog.validateAll() is True
        args = dialog.toArgs()
        assert isinstance(args, dict)
        assert "--deterministic-ids" in args or "--no-deterministic-ids" in args
        assert "--toc" in args or "--no-toc" in args
        dialog.fromArgs({})
        assert not dialog._dirty
        dialog._mark_dirty()
        assert dialog._dirty
        apply_button = dialog.button_box.button(QDialogButtonBox.StandardButton.Apply)
        assert apply_button.isEnabled()

    def test_tab_content_placeholders(self, qtbot):
        """Test that tabs contain placeholder content."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)
        assert dialog.general_tab.layout() is not None
        assert dialog.conversion_tab.layout() is not None
        assert dialog.debug_tab.layout() is not None

    def test_general_tab_controls_exist(self, qtbot):
        """Test that General tab contains all expected controls."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)
        assert hasattr(dialog, "author_edit")
        assert hasattr(dialog, "license_edit")
        assert hasattr(dialog, "pack_name_edit")
        assert hasattr(dialog, "output_dir_selector")
        assert hasattr(dialog, "deterministic_ids_checkbox")
        assert dialog.author_edit.text() == ""
        assert dialog.license_edit.text() == ""
        assert dialog.pack_name_edit.text() == ""
        assert dialog.deterministic_ids_checkbox.isChecked()

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
        assert not dialog._dirty
        assert not apply_button.isEnabled()
        dialog.author_edit.setText("Test Author")
        assert dialog._dirty
        assert apply_button.isEnabled()
        dialog._dirty = False
        apply_button.setEnabled(False)
        dialog.license_edit.setText("MIT")
        assert dialog._dirty
        assert apply_button.isEnabled()
        dialog._dirty = False
        apply_button.setEnabled(False)
        dialog.pack_name_edit.setText("custom-pack")
        assert dialog._dirty
        assert apply_button.isEnabled()
        dialog._dirty = False
        apply_button.setEnabled(False)
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
        args = dialog.toArgs()
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

    def test_debug_tab_controls_exist(self, qtbot):
        """Test that Debug tab contains all expected controls."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)
        assert hasattr(dialog, "verbose_checkbox")
        assert hasattr(dialog, "log_level_combo")
        assert hasattr(dialog, "dry_run_checkbox")
        assert hasattr(dialog, "keep_temp_checkbox")
        assert hasattr(dialog, "log_file_edit")
        assert hasattr(dialog, "browse_log_file_button")
        assert hasattr(dialog, "export_debug_button")
        assert not dialog.verbose_checkbox.isChecked()
        assert dialog.log_level_combo.currentText() == "INFO"
        assert not dialog.dry_run_checkbox.isChecked()
        assert not dialog.keep_temp_checkbox.isChecked()
        assert dialog.log_file_edit.text() == ""
        assert dialog._export_debug_path is None

    def test_debug_tab_tooltips(self, qtbot):
        """Test that Debug tab controls have proper tooltips."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)
        assert "troubleshooting" in dialog.verbose_checkbox.toolTip()
        assert "minimum severity" in dialog.log_level_combo.toolTip()
        assert "Simulate actions" in dialog.dry_run_checkbox.toolTip()
        assert "intermediate files" in dialog.keep_temp_checkbox.toolTip()
        assert "console only" in dialog.log_file_edit.toolTip()
        assert "Browse for log file" in dialog.browse_log_file_button.toolTip()
        assert "diagnostic information" in dialog.export_debug_button.toolTip()

    def test_debug_tab_dirty_state_tracking(self, qtbot):
        """Test that changing Debug tab controls marks dialog as dirty."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)
        apply_button = dialog.button_box.button(dialog.button_box.StandardButton.Apply)
        controls_to_test = [
            (dialog.verbose_checkbox, lambda: dialog.verbose_checkbox.setChecked(True)),
            (dialog.log_level_combo, lambda: dialog.log_level_combo.setCurrentText("DEBUG")),
            (dialog.dry_run_checkbox, lambda: dialog.dry_run_checkbox.setChecked(True)),
            (dialog.keep_temp_checkbox, lambda: dialog.keep_temp_checkbox.setChecked(True)),
            (dialog.log_file_edit, lambda: dialog.log_file_edit.setText("/tmp/test.log")),
        ]
        for control, action in controls_to_test:
            dialog._dirty = False
            apply_button.setEnabled(False)
            action()
            assert dialog._dirty, f"Control {control} did not mark dialog as dirty"
            assert apply_button.isEnabled(), f"Control {control} did not enable Apply button"

    def test_debug_tab_to_args_mapping(self, qtbot):
        """Test that Debug tab controls map correctly to CLI arguments."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)
        dialog.verbose_checkbox.setChecked(True)
        dialog.log_level_combo.setCurrentText("DEBUG")
        dialog.dry_run_checkbox.setChecked(True)
        dialog.keep_temp_checkbox.setChecked(True)
        dialog.log_file_edit.setText("/tmp/debug.log")
        dialog._export_debug_path = "/tmp/debug-bundle.zip"
        args = dialog.toArgs()
        assert args["--verbose"] is True
        assert args["--log-level"] == "DEBUG"
        assert args["--dry-run"] is True
        assert args["--keep-temp"] is True
        assert args["--log-file"] == "/tmp/debug.log"
        assert args["--export-debug"] == "/tmp/debug-bundle.zip"

    def test_debug_tab_default_values_not_in_args(self, qtbot):
        """Test that default values are not included in CLI arguments."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)
        args = dialog.toArgs()
        assert "--verbose" not in args
        assert "--log-level" not in args
        assert "--dry-run" not in args
        assert "--keep-temp" not in args
        assert "--log-file" not in args
        assert "--export-debug" not in args

    def test_debug_tab_from_args_mapping(self, qtbot):
        """Test that CLI arguments populate Debug tab controls correctly."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)
        args = {
            "--verbose": True,
            "--log-level": "ERROR",
            "--dry-run": True,
            "--keep-temp": True,
            "--log-file": "/var/log/pdf2foundry.log",
            "--export-debug": "/home/user/debug.zip",
        }
        dialog.fromArgs(args)
        assert dialog.verbose_checkbox.isChecked()
        assert dialog.log_level_combo.currentText() == "ERROR"
        assert dialog.dry_run_checkbox.isChecked()
        assert dialog.keep_temp_checkbox.isChecked()
        assert dialog.log_file_edit.text() == "/var/log/pdf2foundry.log"
        assert dialog._export_debug_path == "/home/user/debug.zip"

    def test_debug_tab_log_level_validation(self, qtbot):
        """Test that invalid log levels are ignored in fromArgs."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)
        args = {"--log-level": "INVALID"}
        dialog.fromArgs(args)
        assert dialog.log_level_combo.currentText() == "INFO"
        args = {"--log-level": "WARNING"}
        dialog.fromArgs(args)
        assert dialog.log_level_combo.currentText() == "WARNING"

    def test_browse_log_file_handler(self, qtbot, monkeypatch):
        """Test the browse log file button handler."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        def mock_get_save_filename(*args, **kwargs):
            return "/tmp/test.log", "Log Files (*.log *.txt)"

        monkeypatch.setattr("PySide6.QtWidgets.QFileDialog.getSaveFileName", mock_get_save_filename)
        assert not dialog._dirty
        dialog._on_browse_log_file()
        assert dialog.log_file_edit.text() == "/tmp/test.log"
        assert dialog._dirty

    def test_export_debug_handler(self, qtbot, monkeypatch):
        """Test the export debug bundle button handler."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        def mock_get_save_filename(*args, **kwargs):
            return "/tmp/debug-bundle.zip", "ZIP Files (*.zip)"

        monkeypatch.setattr("PySide6.QtWidgets.QFileDialog.getSaveFileName", mock_get_save_filename)
        assert not dialog._dirty
        assert dialog._export_debug_path is None
        dialog._on_export_debug_clicked()
        assert dialog._export_debug_path == "/tmp/debug-bundle.zip"
        assert dialog._dirty

    # New validation tests
    def test_text_field_validation(self, qtbot):
        """Test text field validation with length limits and invalid characters."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Test pack name with invalid characters
        dialog.pack_name_edit.setText("invalid/name")
        assert not dialog._validate_text_field(dialog.pack_name_edit, "Pack name", 64)
        assert dialog.pack_name_edit.property("hasError")

        # Test valid pack name
        dialog.pack_name_edit.setText("valid-name")
        assert dialog._validate_text_field(dialog.pack_name_edit, "Pack name", 64)
        assert not dialog.pack_name_edit.property("hasError")

        # Test length limit
        long_text = "a" * 65
        dialog.pack_name_edit.setText(long_text)
        assert not dialog._validate_text_field(dialog.pack_name_edit, "Pack name", 64)
        assert dialog.pack_name_edit.property("hasError")

    def test_pages_field_validation(self, qtbot):
        """Test pages field validation with various formats."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Test valid page specifications
        valid_specs = ["1", "1,2,3", "1-5", "1,3-5,7", "1-5,10-15"]
        for spec in valid_specs:
            dialog.pages_edit.setText(spec)
            assert dialog._validate_pages_field(), f"Failed for valid spec: {spec}"
            assert not dialog.pages_edit.property("hasError")

        # Test invalid page specifications
        invalid_specs = ["0", "1-0", "abc", "1,2,", "1--5", "1,2-", "-5"]
        for spec in invalid_specs:
            dialog.pages_edit.setText(spec)
            assert not dialog._validate_pages_field(), f"Should fail for invalid spec: {spec}"
            assert dialog.pages_edit.property("hasError")

        # Test empty spec (should be valid)
        dialog.pages_edit.setText("")
        assert dialog._validate_pages_field()
        assert not dialog.pages_edit.property("hasError")

    def test_parse_pages_helper(self, qtbot):
        """Test the _parse_pages helper method."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Test valid cases
        assert dialog._parse_pages("") == []
        assert dialog._parse_pages("1") == [(1, 1)]
        assert dialog._parse_pages("1,3") == [(1, 1), (3, 3)]
        assert dialog._parse_pages("1-5") == [(1, 5)]
        assert dialog._parse_pages("1,3-5,7") == [(1, 1), (3, 5), (7, 7)]

        # Test invalid cases
        assert dialog._parse_pages("0") is None
        assert dialog._parse_pages("1-0") is None
        assert dialog._parse_pages("abc") is None
        assert dialog._parse_pages("1,2,") is None

    def test_vlm_field_dependency_validation(self, qtbot):
        """Test VLM field validation based on picture descriptions checkbox."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # When picture descriptions is off, VLM field should not be required
        dialog.picture_descriptions_checkbox.setChecked(False)
        dialog.vlm_repo_edit.setText("")
        assert dialog.validateAll()

        # When picture descriptions is on, VLM field should be required
        dialog.picture_descriptions_checkbox.setChecked(True)
        dialog.vlm_repo_edit.setText("")
        assert not dialog.validateAll()
        assert dialog.vlm_repo_edit.property("hasError")

        # With valid VLM field, should pass
        dialog.vlm_repo_edit.setText("microsoft/Florence-2-base")
        assert dialog.validateAll()
        assert not dialog.vlm_repo_edit.property("hasError")

    def test_button_states_with_validation(self, qtbot):
        """Test that OK/Apply buttons behave correctly with validation."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        ok_button = dialog.button_box.button(dialog.button_box.StandardButton.Ok)
        apply_button = dialog.button_box.button(dialog.button_box.StandardButton.Apply)

        # Initially should be valid
        assert ok_button.isEnabled()
        assert not apply_button.isEnabled()  # Not dirty yet

        # Make invalid change
        dialog.pack_name_edit.setText("invalid/name")
        dialog._mark_dirty()

        # OK should be disabled due to validation failure, Apply should be enabled (dirty)
        assert not ok_button.isEnabled()
        assert apply_button.isEnabled()  # Apply is enabled when dirty

        # Fix the validation error
        dialog.pack_name_edit.setText("valid-name")

        # Both buttons should be enabled again
        assert ok_button.isEnabled()
        assert apply_button.isEnabled()

    def test_restore_defaults_button(self, qtbot):
        """Test the Restore Defaults button functionality."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Change some values from defaults
        dialog.author_edit.setText("Test Author")
        dialog.toc_checkbox.setChecked(False)
        dialog.verbose_checkbox.setChecked(True)
        dialog.log_level_combo.setCurrentText("DEBUG")

        # Click restore defaults
        restore_button = dialog.button_box.button(dialog.button_box.StandardButton.RestoreDefaults)
        assert restore_button is not None
        dialog.onRestoreDefaults()

        # Check that values are restored to defaults
        assert dialog.author_edit.text() == ""
        assert dialog.toc_checkbox.isChecked()
        assert not dialog.verbose_checkbox.isChecked()
        assert dialog.log_level_combo.currentText() == "INFO"
        assert dialog._dirty

    def test_enhanced_toargs_validation(self, qtbot):
        """Test that toArgs only returns valid arguments."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Set some valid values
        dialog.author_edit.setText("Test Author")
        dialog.pages_edit.setText("1,3-5,7")

        args = dialog.toArgs()
        assert "--author" in args
        assert args["--pages"] == "1,3-5,7"

        # Set invalid pages
        dialog.pages_edit.setText("invalid-pages")

        # toArgs should return empty dict due to validation failure
        args = dialog.toArgs()
        assert len(args) == 0

    def test_fromargs_list_format(self, qtbot):
        """Test fromArgs with list format arguments."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Test with list format
        args_list = ["--author", "John Doe", "--verbose", "--log-level=DEBUG", "--pages", "1,3-5"]
        dialog.fromArgs(args_list)

        assert dialog.author_edit.text() == "John Doe"
        assert dialog.verbose_checkbox.isChecked()
        assert dialog.log_level_combo.currentText() == "DEBUG"
        assert dialog.pages_edit.text() == "1,3-5"

    def test_args_list_parser(self, qtbot):
        """Test the _parse_args_list helper method."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Test various argument formats
        args_list = ["--author", "John Doe", "--verbose", "--log-level=DEBUG", "--pages", "1,3-5"]
        parsed = dialog._parse_args_list(args_list)

        expected = {"--author": "John Doe", "--verbose": True, "--log-level": "DEBUG", "--pages": "1,3-5"}

        assert parsed == expected

    def test_pages_normalization(self, qtbot):
        """Test that pages are normalized in toArgs and fromArgs."""
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Set pages with extra spaces
        dialog.pages_edit.setText(" 1 , 3 - 5 , 7 ")

        args = dialog.toArgs()
        assert args["--pages"] == "1,3-5,7"  # Should be normalized

        # Test fromArgs normalization
        dialog.fromArgs({"--pages": " 1 , 3 - 5 , 7 "})
        assert dialog.pages_edit.text() == "1,3-5,7"  # Should be normalized

    def test_qsettings_persistence_round_trip(self, qtbot, tmp_path, monkeypatch):
        """Test that settings persist correctly across dialog instances."""
        # Use a temporary settings file
        settings_file = tmp_path / "test_settings.ini"

        # Mock QSettings to use our temporary file
        from PySide6.QtCore import QSettings as OriginalQSettings

        class MockQSettings(OriginalQSettings):
            def __init__(self):
                super().__init__(str(settings_file), OriginalQSettings.Format.IniFormat)

        # Patch both the import and the class
        monkeypatch.setattr("PySide6.QtCore.QSettings", MockQSettings)
        monkeypatch.setattr("core.config_manager.QSettings", MockQSettings)

        # Create first dialog and set some values
        dialog1 = SettingsDialog()
        qtbot.addWidget(dialog1)

        dialog1.author_edit.setText("Test Author")
        dialog1.license_edit.setText("MIT")
        dialog1.pack_name_edit.setText("test-pack")
        dialog1.toc_checkbox.setChecked(False)
        dialog1.verbose_checkbox.setChecked(True)
        dialog1.log_level_combo.setCurrentText("DEBUG")
        dialog1.pages_edit.setText("1,3-5")

        # Save settings
        dialog1.saveSettings()

        # Create second dialog and verify values are loaded
        dialog2 = SettingsDialog()
        qtbot.addWidget(dialog2)

        assert dialog2.author_edit.text() == "Test Author"
        assert dialog2.license_edit.text() == "MIT"
        assert dialog2.pack_name_edit.text() == "test-pack"
        assert not dialog2.toc_checkbox.isChecked()
        assert dialog2.verbose_checkbox.isChecked()
        assert dialog2.log_level_combo.currentText() == "DEBUG"
        assert dialog2.pages_edit.text() == "1,3-5"

    def test_qsettings_defaults_on_first_run(self, qtbot, tmp_path, monkeypatch):
        """Test that appropriate defaults are set on first run."""
        # Use a temporary settings file that doesn't exist
        settings_file = tmp_path / "empty_settings.ini"

        from PySide6.QtCore import QSettings as OriginalQSettings

        class MockQSettings(OriginalQSettings):
            def __init__(self):
                super().__init__(str(settings_file), OriginalQSettings.Format.IniFormat)

        # Patch both the import and the class
        monkeypatch.setattr("PySide6.QtCore.QSettings", MockQSettings)
        monkeypatch.setattr("core.config_manager.QSettings", MockQSettings)

        # Create dialog - should load defaults
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Check that defaults are set correctly
        assert dialog.author_edit.text() == ""
        assert dialog.license_edit.text() == ""
        assert dialog.pack_name_edit.text() == ""
        assert dialog.deterministic_ids_checkbox.isChecked()
        assert dialog.toc_checkbox.isChecked()
        assert dialog.tables_combo.currentText() == "auto"
        assert dialog.ocr_combo.currentText() == "auto"
        assert not dialog.picture_descriptions_checkbox.isChecked()
        assert not dialog.verbose_checkbox.isChecked()
        assert dialog.log_level_combo.currentText() == "INFO"

    def test_save_settings_only_when_valid(self, qtbot, tmp_path, monkeypatch):
        """Test that saveSettings only saves when validation passes."""
        settings_file = tmp_path / "validation_test.ini"

        from PySide6.QtCore import QSettings as OriginalQSettings

        class MockQSettings(OriginalQSettings):
            def __init__(self):
                super().__init__(str(settings_file), OriginalQSettings.Format.IniFormat)

        # Patch both the import and the class
        monkeypatch.setattr("PySide6.QtCore.QSettings", MockQSettings)
        monkeypatch.setattr("core.config_manager.QSettings", MockQSettings)

        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Set invalid data
        dialog.pack_name_edit.setText("invalid/name")
        dialog.pages_edit.setText("invalid-pages")

        # Try to save - should not save due to validation failure
        dialog.saveSettings()

        # Create new dialog and verify invalid data was not saved
        dialog2 = SettingsDialog()
        qtbot.addWidget(dialog2)

        # Should have defaults, not the invalid values
        assert dialog2.pack_name_edit.text() == ""
        assert dialog2.pages_edit.text() == ""
