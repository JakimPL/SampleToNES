from dataclasses import dataclass
from typing import Optional

from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import GeneratorName


@dataclass(frozen=True)
class TrackerCursor:
    row: int
    generator: Optional[GeneratorName]
    subcolumn: SubColumn
