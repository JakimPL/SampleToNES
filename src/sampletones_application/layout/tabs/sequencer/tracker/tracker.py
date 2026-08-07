from pydantic import BaseModel

from sampletones_application.layout.tabs.sequencer.tracker.subcolumn import SubcolumnWidths


class TrackerLayout(BaseModel, extra="forbid", frozen=True):
    rows: int
    page_size: int
    subcolumn_widths: SubcolumnWidths
    channel_column_tint: float
    muted_text_fraction: float
