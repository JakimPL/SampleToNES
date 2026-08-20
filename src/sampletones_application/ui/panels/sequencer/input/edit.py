from typing import Optional

from pydantic.dataclasses import dataclass

from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName


@dataclass(frozen=True)
class EditAction:
    row: int
    channel: Optional[ChannelName]
    sample_index: Optional[int]
    transpose: Optional[int]
    volume: Optional[int]
    note_off: bool = False


@dataclass
class ClearAction:
    row: int
    channel: Optional[ChannelName]
    subcolumn: Optional[SubColumn] = None
