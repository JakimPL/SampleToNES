from typing import Tuple

from pydantic import BaseModel

from sampletones_core.constants.enums import GeneratorName


class OrderEntryViewModel(BaseModel, frozen=True):
    position: int
    pattern_id: str
    pattern_label: str


class SequencerOrderViewModel(BaseModel, frozen=True):
    """The pattern sequence for one channel."""

    generator: GeneratorName
    entries: Tuple[OrderEntryViewModel, ...]
