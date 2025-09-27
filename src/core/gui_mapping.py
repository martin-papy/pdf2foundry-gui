"""
GUI to ConversionConfig mapping layer.

This module provides functionality to map GUI widget states to ConversionConfig
instances, using the CLI definitions as the source of truth for validation and defaults.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from .conversion_config import ConversionConfig, OcrMode, PictureDescriptionMode, TableMode
from .page_utils import parse_page_range
from .validation import ValidationError, validate_and_normalize


class GuiMappingError(Exception):
    """Exception raised when GUI mapping fails."""

    def __init__(self, message: str, field: str | None = None):
        """
        Initialize the mapping error.

        Args:
            message: Error message
            field: GUI field that caused the error (if applicable)
        """
        super().__init__(message)
        self.field = field


class GuiConfigMapper:
    """
    Maps GUI widget states to ConversionConfig instances.

    This class provides a deterministic mapping from GUI state dictionaries
    to validated ConversionConfig objects, handling type coercion, validation,
    and default fallbacks.
    """

    # Mapping from GUI widget keys to ConversionConfig field names
    FIELD_MAPPING: ClassVar[dict[str, str]] = {
        # Main window fields
        "pdf_path": "pdf",
        "mod_id": "mod_id",
        "mod_title": "mod_title",
        # General tab fields
        "author": "author",
        "license": "license",
        "pack_name": "pack_name",
        "output_dir": "out_dir",
        "deterministic_ids": "deterministic_ids",
        # Conversion tab fields
        "toc": "toc",
        "tables": "tables",
        "ocr": "ocr",
        "picture_descriptions": "picture_descriptions",
        "vlm_repo_id": "vlm_repo_id",
        "pages": "pages",
        # Performance/advanced fields (if they exist in GUI)
        "workers": "workers",
        "reflow_columns": "reflow_columns",
        "compile_pack": "compile_pack",
        "docling_json": "docling_json",
        "write_docling_json": "write_docling_json",
        "verbose": "verbose",
        "no_ml": "no_ml",
    }

    def build_config_from_gui(self, gui_state: dict[str, Any]) -> ConversionConfig:
        """
        Build a ConversionConfig from GUI state dictionary.

        Args:
            gui_state: Dictionary containing GUI widget values

        Returns:
            Validated ConversionConfig instance

        Raises:
            GuiMappingError: If mapping or validation fails
        """
        try:
            # Start with default config
            config_data = {}

            # Map GUI fields to config fields
            for gui_key, config_field in self.FIELD_MAPPING.items():
                if gui_key in gui_state:
                    gui_value = gui_state[gui_key]
                    config_data[config_field] = self._convert_gui_value(gui_key, gui_value, config_field)

            # Create config from mapped data
            config = ConversionConfig.from_dict(config_data)

            # Validate and normalize
            validated_config = validate_and_normalize(config)

            return validated_config

        except ValidationError as e:
            # Map validation errors back to GUI field names
            gui_field = self._map_config_field_to_gui(e.field or "")
            raise GuiMappingError(f"Validation failed for {gui_field or e.field}: {e.message}", field=gui_field) from e

        except Exception as e:
            raise GuiMappingError(f"Failed to build config from GUI state: {e}") from e

    def _convert_gui_value(self, gui_key: str, gui_value: Any, config_field: str) -> Any:
        """
        Convert a GUI widget value to the appropriate config field value.

        Args:
            gui_key: GUI widget key
            gui_value: Raw value from GUI widget
            config_field: Target config field name

        Returns:
            Converted value suitable for ConversionConfig

        Raises:
            GuiMappingError: If conversion fails
        """
        try:
            # Path fields
            if config_field in ["pdf", "out_dir", "docling_json"]:
                if gui_value is None:
                    return None
                elif isinstance(gui_value, str):
                    if not gui_value.strip():
                        return None
                    return Path(gui_value.strip())
                elif isinstance(gui_value, Path):
                    return gui_value
                else:
                    return Path(str(gui_value))

            # String fields
            if config_field in ["mod_id", "mod_title", "author", "license", "pack_name", "vlm_repo_id"]:
                return str(gui_value).strip() if gui_value is not None else ""

            # Boolean fields
            if config_field in ["toc", "deterministic_ids", "compile_pack", "reflow_columns", "write_docling_json", "no_ml"]:
                if isinstance(gui_value, bool):
                    return gui_value
                elif isinstance(gui_value, str):
                    return gui_value.lower() in ("true", "1", "yes", "on")
                else:
                    return bool(gui_value)

            # Enum fields
            if config_field == "tables":
                if isinstance(gui_value, TableMode):
                    return gui_value
                return TableMode(str(gui_value))

            if config_field == "ocr":
                if isinstance(gui_value, OcrMode):
                    return gui_value
                return OcrMode(str(gui_value))

            if config_field == "picture_descriptions":
                if isinstance(gui_value, PictureDescriptionMode):
                    return gui_value
                # Handle checkbox boolean -> enum conversion
                if isinstance(gui_value, bool):
                    return PictureDescriptionMode.ON if gui_value else PictureDescriptionMode.OFF
                return PictureDescriptionMode(str(gui_value))

            # Numeric fields
            if config_field in ["workers", "verbose"]:
                if isinstance(gui_value, int | float):
                    return int(gui_value)
                elif isinstance(gui_value, str):
                    return int(gui_value) if gui_value.strip() else 1
                else:
                    return int(gui_value)

            # Page range field (special handling)
            if config_field == "pages":
                if not gui_value or (isinstance(gui_value, str) and not gui_value.strip()):
                    return None

                if isinstance(gui_value, list):
                    # Already a list of page numbers
                    return gui_value
                elif isinstance(gui_value, str):
                    # Parse page range string
                    try:
                        return parse_page_range(gui_value.strip())
                    except ValidationError as e:
                        raise GuiMappingError(f"Invalid page range format: {e.message}", field=gui_key) from e
                else:
                    raise GuiMappingError(f"Invalid page range format: {gui_value}", field=gui_key)

            # Default: return as-is
            return gui_value

        except (ValueError, TypeError) as e:
            raise GuiMappingError(f"Failed to convert GUI value for {gui_key}: {e}", field=gui_key) from e

    def _map_config_field_to_gui(self, config_field: str) -> str | None:
        """
        Map a config field name back to GUI field name.

        Args:
            config_field: ConversionConfig field name

        Returns:
            GUI field name, or None if not found
        """
        for gui_key, mapped_field in self.FIELD_MAPPING.items():
            if mapped_field == config_field:
                return gui_key
        return None

    def extract_gui_state_from_settings_dialog(self, dialog: Any) -> dict[str, Any]:
        """
        Extract GUI state from a SettingsDialog instance.

        This method knows about the specific widget structure of the SettingsDialog
        and extracts values from the appropriate widgets.

        Args:
            dialog: SettingsDialog instance

        Returns:
            Dictionary of GUI state values

        Raises:
            GuiMappingError: If extraction fails
        """
        try:
            gui_state = {}

            # Extract from General tab
            if hasattr(dialog, "author_edit"):
                gui_state["author"] = dialog.author_edit.text()

            if hasattr(dialog, "license_edit"):
                gui_state["license"] = dialog.license_edit.text()

            if hasattr(dialog, "pack_name_edit"):
                gui_state["pack_name"] = dialog.pack_name_edit.text()

            if hasattr(dialog, "output_dir_selector"):
                gui_state["output_dir"] = dialog.output_dir_selector.path()

            if hasattr(dialog, "deterministic_ids_checkbox"):
                gui_state["deterministic_ids"] = dialog.deterministic_ids_checkbox.isChecked()

            # Extract from Conversion tab
            if hasattr(dialog, "toc_checkbox"):
                gui_state["toc"] = dialog.toc_checkbox.isChecked()

            if hasattr(dialog, "tables_combo"):
                gui_state["tables"] = dialog.tables_combo.currentText()

            if hasattr(dialog, "ocr_combo"):
                gui_state["ocr"] = dialog.ocr_combo.currentText()

            if hasattr(dialog, "picture_descriptions_checkbox"):
                gui_state["picture_descriptions"] = dialog.picture_descriptions_checkbox.isChecked()

            if hasattr(dialog, "vlm_repo_edit"):
                vlm_text = dialog.vlm_repo_edit.text().strip()
                gui_state["vlm_repo_id"] = vlm_text if vlm_text else None

            if hasattr(dialog, "pages_edit"):
                pages_text = dialog.pages_edit.text().strip()
                gui_state["pages"] = pages_text if pages_text else None

            # Extract debug/advanced options if they exist
            # (These might not be in the current GUI but could be added later)

            return gui_state

        except Exception as e:
            raise GuiMappingError(f"Failed to extract GUI state: {e}") from e

    def extract_gui_state_from_main_window(self, main_window: Any) -> dict[str, Any]:
        """
        Extract GUI state from the main window.

        This extracts the basic required fields from the main window interface.

        Args:
            main_window: Main window instance

        Returns:
            Dictionary of GUI state values

        Raises:
            GuiMappingError: If extraction fails
        """
        try:
            gui_state = {}

            # Extract PDF path from drag-drop or file selector
            if hasattr(main_window, "drag_drop_label") and hasattr(main_window.drag_drop_label, "file_path"):
                pdf_path = main_window.drag_drop_label.file_path
                if pdf_path:
                    gui_state["pdf_path"] = pdf_path

            # Extract mod_id and mod_title if they exist in main window
            # (These might be in a quick settings area or derived from filename)

            return gui_state

        except Exception as e:
            raise GuiMappingError(f"Failed to extract main window state: {e}") from e

    def merge_gui_states(self, *states: dict[str, Any]) -> dict[str, Any]:
        """
        Merge multiple GUI state dictionaries.

        Later states override earlier ones for conflicting keys.

        Args:
            *states: GUI state dictionaries to merge

        Returns:
            Merged GUI state dictionary
        """
        merged = {}
        for state in states:
            merged.update(state)
        return merged


# Convenience functions
def build_config_from_gui(gui_state: dict[str, Any]) -> ConversionConfig:
    """
    Convenience function to build a ConversionConfig from GUI state.

    Args:
        gui_state: Dictionary containing GUI widget values

    Returns:
        Validated ConversionConfig instance

    Raises:
        GuiMappingError: If mapping or validation fails
    """
    mapper = GuiConfigMapper()
    return mapper.build_config_from_gui(gui_state)


def extract_full_gui_state(main_window: Any, settings_dialog: Any | None = None) -> dict[str, Any]:
    """
    Extract complete GUI state from main window and optional settings dialog.

    Args:
        main_window: Main window instance
        settings_dialog: Optional settings dialog instance

    Returns:
        Complete GUI state dictionary

    Raises:
        GuiMappingError: If extraction fails
    """
    mapper = GuiConfigMapper()

    # Extract from main window
    main_state = mapper.extract_gui_state_from_main_window(main_window)

    # Extract from settings dialog if provided
    if settings_dialog:
        settings_state = mapper.extract_gui_state_from_settings_dialog(settings_dialog)
        return mapper.merge_gui_states(main_state, settings_state)

    return main_state
