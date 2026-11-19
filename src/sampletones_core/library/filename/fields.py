from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.constants.enums import SpectrumMethod
from sampletones_core.constants.field_aliases import ALIASES
from sampletones_shared.paths.extensions import EXT_FILE_LIBRARY
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.hashing import HASH_PATTERN
from sampletones_shared.utils.key_value import key_value_name, parse_key_value_name
from sampletones_shared.utils.system.paths import get_filename


class InstructionsFilenameFields(BaseModel):
    """The settings a library file's name spells: ``sr_…_nf_…_ws_…_tg_…_sm_…_ch_…``."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    sr: int = Field(gt=0, validation_alias=ALIASES["sr"])
    nf: int = Field(gt=0, validation_alias=ALIASES["nf"])
    ws: int = Field(gt=0, validation_alias=ALIASES["ws"])
    tg: int = Field(ge=0, validation_alias=ALIASES["tg"])
    sm: SpectrumMethod = Field(validation_alias=ALIASES["sm"])
    ch: str = Field(pattern=HASH_PATTERN, validation_alias=ALIASES["ch"])

    @property
    def stem(self) -> str:
        return key_value_name(self)

    @property
    def filename(self) -> str:
        return get_filename(self.stem, EXT_FILE_LIBRARY)

    @classmethod
    def parse(cls, pathlike: Pathlike) -> Optional[InstructionsFilenameFields]:
        """The fields a file's name states, or ``None`` where it is not a name a library is written
        under: its extension aside, the name must be the one :attr:`stem` writes."""
        return parse_key_value_name(Path(pathlike).stem, cls)
