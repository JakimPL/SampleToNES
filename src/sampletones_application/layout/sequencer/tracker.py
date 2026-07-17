from pydantic import BaseModel


class SubcolumnWidths(BaseModel, extra="forbid", frozen=True):
    instrument: int
    transpose: int
    volume: int


class TrackerLayout(BaseModel, extra="forbid", frozen=True):
    rows: int
    row_height: int
    page_size: int
    subcolumn_widths: SubcolumnWidths
    channel_column_tint: float
