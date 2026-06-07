from typing import Tuple

from pydantic import BaseModel

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.utils.display import display_id


class OrderEntryViewModel(BaseModel, frozen=True):
    position: int
    pattern_id: str
    pattern_index: int

    @property
    def label(self) -> str:
        return display_id(self.pattern_index)


class SequencerOrderViewModel(BaseModel, frozen=True):
    """The pattern sequence for one channel."""

    generator: GeneratorName
    entries: Tuple[OrderEntryViewModel, ...]
