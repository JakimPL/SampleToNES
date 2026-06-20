from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Final

from pydantic import BaseModel, Field

from sampletones_core.paths import EXT_FILE_LIBRARY
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.serialization import HASH_LENGTH

FILENAME_SEPARATOR: Final[str] = "_"


class InstructionsFilenameFields(BaseModel):
    sr: int = Field(gt=0)
    nf: int = Field(gt=0)
    ws: int = Field(gt=0)
    tg: int = Field(ge=0)
    ch: str = Field(pattern=rf"^[0-9a-f]{ {HASH_LENGTH} }$")

    @property
    def stem(self) -> str:
        pairs = (FILENAME_SEPARATOR.join([key, str(value)]) for key, value in self.model_dump().items())
        return FILENAME_SEPARATOR.join(pairs)

    @property
    def filename(self) -> str:
        return f"{self.stem}{EXT_FILE_LIBRARY}"

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
