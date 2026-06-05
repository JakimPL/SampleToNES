from dataclasses import dataclass
from typing import Optional

from ...project.patterns.display import display_id, display_transpose, display_volume
from .row import Row


@dataclass(frozen=True)
class SampleRow(Row):
    sample_id: Optional[int]
    volume: Optional[int]
    transpose: Optional[int]

    def __str__(self) -> str:
        sample_id = display_id(self.sample_id)
        volume = display_volume(self.volume)
        transpose = display_transpose(self.transpose)
        return f"{sample_id} {volume} {transpose}"
