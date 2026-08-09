from pydantic import BaseModel

from sampletones_application.layout.tabs.sequencer.tracker.subcolumn import SubcolumnWidths


class TrackerLayout(BaseModel, extra="forbid", frozen=True):
    """The tracker's row counts, column widths and tint strengths.

    ``rows_per_beat`` and ``rows_per_bar`` say how the pattern is grouped: every row whose
    index is a multiple of one of them opens that group and takes the emphasis its colour
    carries. A count of zero leaves the rows evenly weighted.
    """

    rows: int
    page_size: int
    rows_per_beat: int
    rows_per_bar: int
    subcolumn_widths: SubcolumnWidths
    channel_column_tint: float
    muted_text_fraction: float
