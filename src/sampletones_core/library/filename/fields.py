from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Final

from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.constants.enums import SpectrumMethod
from sampletones_core.constants.field_aliases import ALIASES
from sampletones_shared.paths.extensions import EXT_FILE_LIBRARY
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.serialization import HASH_PATTERN
from sampletones_shared.utils.system.paths import get_filename

FILENAME_SEPARATOR: Final[str] = "_"


class InstructionsFilenameFields(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sr: int = Field(gt=0, validation_alias=ALIASES["sr"])
    nf: int = Field(gt=0, validation_alias=ALIASES["nf"])
    ws: int = Field(gt=0, validation_alias=ALIASES["ws"])
    tg: int = Field(ge=0, validation_alias=ALIASES["tg"])
    sm: SpectrumMethod = Field(validation_alias=ALIASES["sm"])
    ch: str = Field(pattern=HASH_PATTERN, validation_alias=ALIASES["ch"])

    @property
    def stem(self) -> str:
        pairs = (FILENAME_SEPARATOR.join([key, str(value)]) for key, value in self.model_dump().items())
        return FILENAME_SEPARATOR.join(pairs)

    @property
    def filename(self) -> str:
        return get_filename(self.stem, EXT_FILE_LIBRARY)

    @classmethod
    def create(cls, pathlike: Pathlike) -> InstructionsFilenameFields:
        dictionary: Dict[str, Any] = {}
        filename = Path(pathlike).stem
        parts = filename.removesuffix(EXT_FILE_LIBRARY).split(FILENAME_SEPARATOR)

        expected_parts = 2 * len(InstructionsFilenameFields.model_fields)
        if len(parts) != expected_parts:
            raise ValueError(f"Expected {expected_parts} parts separated by '{FILENAME_SEPARATOR}', got {len(parts)}")

        for i, (key, field_info) in enumerate(InstructionsFilenameFields.model_fields.items()):
            try:
                part_key, part_value = parts[2 * i : 2 * i + 2]
            except ValueError as exception:
                raise ValueError(
                    f"Expected {expected_parts} parts separated by '{FILENAME_SEPARATOR}', got {len(parts)}"
                ) from exception

            if key != part_key:
                raise ValueError(f"Malformed filename, expected key '{key}', got '{part_key}' at position {i}")

            value_type = field_info.annotation
            if value_type is None:
                raise SystemError(f"Missing annotated type for key {key}")

            dictionary[key] = value_type(part_value)

        return InstructionsFilenameFields(**dictionary)
