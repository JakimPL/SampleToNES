from typing import Optional

from pydantic.dataclasses import dataclass

from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.patterns.pitch import RowPitch


@dataclass(frozen=True)
class EditAction:
    row: int
    channel: Optional[ChannelName]
    sample_index: Optional[int]
    pitch: Optional[RowPitch]
    volume: Optional[int]
    note_off: bool = False


@dataclass
class ClearAction:
    row: int
    channel: Optional[ChannelName]
    subcolumn: Optional[SubColumn] = None
