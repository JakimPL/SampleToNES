from typing import Dict, Optional

from pydantic.dataclasses import dataclass

from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.patterns.pitch import RowPitch


@dataclass(frozen=True)
class EditAction:
    """One cell edit: the values it writes, each ``None`` where the cell keeps what it holds.

    Attributes:
        levels: The volume a struck key writes on each channel the edit reaches, in place of ``volume``; a
            channel it leaves out, such as the triangle, keeps the volume it holds.
    """

    row: int
    channel: Optional[ChannelName]
    sample_index: Optional[int]
    pitch: Optional[RowPitch]
    volume: Optional[int]
    levels: Optional[Dict[ChannelName, int]]
    note_off: bool = False


@dataclass(frozen=True)
class EnteredNote:
    """The cell a note was entered in: its row, and its channel, ``None`` for the sample column."""

    row: int
    channel: Optional[ChannelName]


@dataclass
class ClearAction:
    row: int
    channel: Optional[ChannelName]
    subcolumn: Optional[SubColumn] = None
