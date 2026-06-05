from dataclasses import dataclass
from typing import Optional

from sampletones_core.constants.enums import GeneratorName

from ...project.patterns.display import display_id, display_pitch, display_volume
from .row import Row


@dataclass(frozen=True)
class GeneratorRow(Row):
    generator: GeneratorName
    pitch: Optional[int]
    instrument_id: Optional[int]
    volume: Optional[int]

    def __str__(self) -> str:
        pitch = display_pitch(self.pitch, self.generator)
        instrument_id = display_id(self.instrument_id)
        volume = display_volume(self.volume)
        return f"{pitch} {instrument_id} {volume}"
