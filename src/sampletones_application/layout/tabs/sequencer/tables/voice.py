from pydantic import BaseModel


class VoiceColumnWidths(BaseModel, extra="forbid", frozen=True):
    """Widths of the three sub-columns that make up a voice row: its kind mark, its id and
    its name. They only mean anything as a set, so they live together.
    """

    kind: int
    id: int
    name: int
