from typing import Optional

from pydantic.dataclasses import dataclass

from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import GeneratorName


@dataclass(frozen=True)
class EditAction:
    row: int
    generator: Optional[GeneratorName]
    sample_index: Optional[int]
    transpose: Optional[int]
    volume: Optional[int]
    note_off: bool = False


@dataclass
class ClearAction:
    row: int
    generator: Optional[GeneratorName]
    subcolumn: Optional[SubColumn] = None
