from pydantic import BaseModel


class InstrumentColumnWidths(BaseModel, extra="forbid", frozen=True):
    """Widths of the three sub-columns that make up an instrument row: its id, its
    name, and its loop marker. They only mean anything as a set, so they live together.
    """

    id: int
    name: int
    loop: int


class SequencerTableCells(BaseModel, extra="forbid", frozen=True):
    row: int
    sample: int
    divider: int
    generator: int
    instrument: InstrumentColumnWidths
