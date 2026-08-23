from pydantic import BaseModel, ConfigDict


class NoteOff(BaseModel):
    """A note-off command in a tracker row's note column: silence the channel's sounding voice.

    Distinct from an empty cell (no command at all): an empty cell lets a sustaining or looped
    voice keep playing, whereas a note-off explicitly cuts it. Carries no data — its presence is
    the command — and is rendered as ``--``. ``extra="forbid"`` keeps it disjoint from
    :class:`Instrument` so the note-column union round-trips unambiguously.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
