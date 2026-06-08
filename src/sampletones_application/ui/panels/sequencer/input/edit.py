from typing import Optional

from pydantic.dataclasses import dataclass

from sampletones_application.ui.panels.sequencer.input.subcolumn import SubColumn
from sampletones_core.constants.enums import GeneratorName


@dataclass(frozen=True)
class EditAction:
    row: int
    generator: Optional[GeneratorName]
    sample_index: Optional[int]
    transpose: Optional[int]
    volume: Optional[int]


@dataclass
class ClearAction:
    row: int
    generator: Optional[GeneratorName]
    subcolumn: Optional[SubColumn] = None
    """The subcolumn to clear, or ``None`` to clear the whole row."""
