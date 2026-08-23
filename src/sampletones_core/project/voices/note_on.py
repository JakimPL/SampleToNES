from pydantic import BaseModel, ConfigDict, Field


class NoteOn(BaseModel):
    """A note-on command in a tracker row's note column: start the named voice on this channel.

    The voice is referenced by its stable ``id``, so the reference survives reordering of the
    project's voice collection. The channel a voice sounds on is the one whose pattern holds the
    row, which is what lets one voice be started on any channel it suits.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    voice_id: str = Field(..., description="Stable id of the voice to start.")
