from dataclasses import dataclass
from typing import Optional

from sampletones_application.ui.panels.sequencer.input.subcolumn import SubColumns
from sampletones_core.constants.enums import GeneratorName


@dataclass(frozen=True)
class TrackerCursor:
    row: int
    generator: Optional[GeneratorName]
    subcolumn: SubColumns
