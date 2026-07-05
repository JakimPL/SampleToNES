from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.constants.general import (
    MAX_TRANSPOSE,
    MAX_VOLUME,
    MIN_TRANSPOSE,
)
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.note_off import NoteOff

NoteCommand = Union[Instrument, NoteOff]


class Row(BaseModel):
    """A single tracker line on one channel.

    The note column holds a :data:`NoteCommand`: an :class:`Instrument` reference, a
    :class:`NoteOff`, or ``None`` for an empty cell. Transpose and volume are independent optional
    columns. A fully empty row (no command, no transpose, no volume) is a blank line.
    """

    model_config = ConfigDict(frozen=True)

    command: Optional[NoteCommand] = Field(
        default=None,
        description="Note-column command: a sample reference, a note-off, or None for an empty cell.",
    )
    transpose: Optional[int] = Field(
        default=None,
        ge=MIN_TRANSPOSE,
        le=MAX_TRANSPOSE,
        description="Note pitch, or None for an empty cell.",
    )
    volume: Optional[int] = Field(
        default=None,
        ge=0,
        le=MAX_VOLUME,
        description="Volume column, or None for an empty cell.",
    )

    def is_empty(self) -> bool:
        return self.command is None and self.transpose is None and self.volume is None

    def references_sample(self, sample_id: str) -> bool:
        command = self.command
        return isinstance(command, Instrument) and command.sample_id == sample_id
