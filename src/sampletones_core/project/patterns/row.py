from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.constants.general import MAX_VOLUME, SILENT_VOLUME
from sampletones_core.project.patterns.pitch import RowPitch
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn

NoteCommand = Union[NoteOn, NoteOff]


class Row(BaseModel):
    """A single tracker line on one channel.

    The note column holds a :data:`NoteCommand`: a :class:`NoteOn` naming the voice to start, a
    :class:`NoteOff`, or ``None`` for an empty cell. The pitch column holds a :class:`Note` the
    channel sounds or a :class:`Step` from the voice's own reference, stored as it was written. A
    fully empty row (no command, no pitch, no volume) is a blank line.
    """

    model_config = ConfigDict(frozen=True)

    command: Optional[NoteCommand] = Field(
        default=None,
        description="Note-column command: a voice reference, a note-off, or None for an empty cell.",
    )
    pitch: Optional[RowPitch] = Field(
        default=None,
        description="The note the channel sounds or the step from the voice's reference, or None for an empty cell.",
    )
    volume: Optional[int] = Field(
        default=None,
        ge=SILENT_VOLUME,
        le=MAX_VOLUME,
        description="Volume column, where SILENT_VOLUME silences the channel, or None for an empty cell.",
    )

    def is_empty(self) -> bool:
        return self.command is None and self.pitch is None and self.volume is None

    def references_voice(self, voice_id: str) -> bool:
        command = self.command
        return isinstance(command, NoteOn) and command.voice_id == voice_id
