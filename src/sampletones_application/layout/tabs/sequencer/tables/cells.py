from pydantic import BaseModel

from sampletones_application.layout.tabs.sequencer.tables.instrument import InstrumentColumnWidths


class SequencerTableCells(BaseModel, extra="forbid", frozen=True):
    row: int
    sample: int
    divider: int
    channel: int
    instrument: InstrumentColumnWidths
