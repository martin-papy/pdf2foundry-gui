"""
ConversionConfig dataclass for pdf2foundry CLI parameter mapping.

This module provides a typed configuration class that mirrors all pdf2foundry CLI options
with proper defaults and validation. It serves as the bridge between GUI state and
backend function calls.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class TableMode(Enum):
    """Table handling mode options."""

    STRUCTURED = "structured"
    AUTO = "auto"
    IMAGE_ONLY = "image-only"


class OcrMode(Enum):
    """OCR processing mode options."""

    AUTO = "auto"
    ON = "on"
    OFF = "off"


class PictureDescriptionMode(Enum):
    """Picture description generation mode options."""

    ON = "on"
    OFF = "off"


@dataclass
class ConversionConfig:
    """
    Configuration for pdf2foundry conversion operations.

    This dataclass mirrors all CLI options from the pdf2foundry convert command,
    providing type safety and default values that match the CLI behavior.
    """

    # Required parameters
    pdf: Path | None = None
    mod_id: str = ""
    mod_title: str = ""

    # Optional metadata
    author: str = ""
    license: str = ""
    pack_name: str = ""  # Default will be computed from mod_id if empty

    # Core behavior flags
    toc: bool = True
    deterministic_ids: bool = True
    out_dir: Path = field(default_factory=lambda: Path("dist"))
    compile_pack: bool = False

    # Content processing
    tables: TableMode = TableMode.AUTO
    ocr: OcrMode = OcrMode.AUTO
    picture_descriptions: PictureDescriptionMode = PictureDescriptionMode.OFF
    vlm_repo_id: str | None = None

    # Performance options
    pages: list[int] | None = None
    workers: int = 1
    reflow_columns: bool = False

    # Docling JSON cache options
    docling_json: Path | None = None
    write_docling_json: bool = False
    fallback_on_json_failure: bool = True

    # Additional options from run_conversion_pipeline
    verbose: int = 0
    no_ml: bool = False

    @classmethod
    def from_cli_defaults(cls) -> ConversionConfig:
        """
        Create a ConversionConfig with defaults matching the CLI parser.

        Returns:
            ConversionConfig with CLI-compatible defaults
        """
        return cls()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConversionConfig:
        """
        Create a ConversionConfig from a dictionary (e.g., from GUI state).

        Args:
            data: Dictionary containing configuration values

        Returns:
            ConversionConfig instance

        Raises:
            ValueError: If invalid enum values are provided
        """
        # Create a copy to avoid modifying the original
        config_data = data.copy()

        # Convert string paths to Path objects
        for path_field in ["pdf", "out_dir", "docling_json"]:
            if path_field in config_data and config_data[path_field] is not None:
                config_data[path_field] = Path(config_data[path_field])

        # Convert string enum values to enum instances
        if "tables" in config_data and isinstance(config_data["tables"], str):
            config_data["tables"] = TableMode(config_data["tables"])

        if "ocr" in config_data and isinstance(config_data["ocr"], str):
            config_data["ocr"] = OcrMode(config_data["ocr"])

        if "picture_descriptions" in config_data and isinstance(config_data["picture_descriptions"], str):
            config_data["picture_descriptions"] = PictureDescriptionMode(config_data["picture_descriptions"])

        # Filter out keys that aren't valid fields
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in config_data.items() if k in valid_fields}

        return cls(**filtered_data)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the configuration to a dictionary for serialization/logging.

        Returns:
            Dictionary representation of the configuration
        """
        result = {}

        for field_name, _field_info in self.__dataclass_fields__.items():
            value = getattr(self, field_name)

            # Convert Path objects to strings
            if isinstance(value, Path):
                result[field_name] = str(value)
            # Convert enums to their string values
            elif isinstance(value, Enum):
                result[field_name] = value.value
            else:
                result[field_name] = value

        return result

    def to_core_kwargs(self) -> dict[str, Any]:
        """
        Convert the configuration to kwargs suitable for run_conversion_pipeline.

        Returns:
            Dictionary of keyword arguments for the core conversion function
        """
        # Compute pack_name default if not provided
        pack_name = self.pack_name or f"{self.mod_id}-journals"

        return {
            "pdf": self.pdf,
            "mod_id": self.mod_id,
            "mod_title": self.mod_title,
            "out_dir": self.out_dir,
            "pack_name": pack_name,
            "author": self.author,
            "license": self.license,
            "toc": self.toc,
            "tables": self.tables.value,
            "deterministic_ids": self.deterministic_ids,
            "compile_pack_now": self.compile_pack,
            "docling_json": self.docling_json,
            "write_docling_json": self.write_docling_json,
            "fallback_on_json_failure": self.fallback_on_json_failure,
            "ocr": self.ocr.value,
            "picture_descriptions": self.picture_descriptions.value,
            "vlm_repo_id": self.vlm_repo_id,
            "pages": self.pages,
            "workers": self.workers,
            "reflow_columns": self.reflow_columns,
            "verbose": self.verbose,
            "no_ml": self.no_ml,
        }

    def validate_required_fields(self) -> list[str]:
        """
        Check if all required fields are provided.

        Returns:
            List of missing required field names (empty if all are provided)
        """
        missing = []

        if not self.pdf:
            missing.append("pdf")
        if not self.mod_id:
            missing.append("mod_id")
        if not self.mod_title:
            missing.append("mod_title")

        return missing

    def normalize_paths(self) -> ConversionConfig:
        """
        Normalize all path fields by expanding user/vars and converting to absolute paths.

        Returns:
            New ConversionConfig instance with normalized paths
        """
        normalized_data = self.to_dict()

        # Normalize path fields
        for path_field in ["pdf", "out_dir", "docling_json"]:
            if path_field in normalized_data and normalized_data[path_field] is not None:
                path_str = str(normalized_data[path_field])
                expanded = os.path.expanduser(os.path.expandvars(path_str))
                normalized_data[path_field] = str(Path(expanded).resolve())

        return self.from_dict(normalized_data)
