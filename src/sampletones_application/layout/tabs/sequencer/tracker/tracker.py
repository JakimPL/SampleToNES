from pydantic import BaseModel

from sampletones_application.layout.tabs.sequencer.tracker.subcolumn import SubcolumnWidths


class TrackerLayout(BaseModel, extra="forbid", frozen=True):
    """The tracker's row counts, column widths and tint strengths.

    The grouping the rows are tinted by is the project's own metre, read from its highlights,
    so this model carries the geometry alone.
    """

    rows: int
    page_size: int
    subcolumn_widths: SubcolumnWidths
    channel_column_tint: float
    muted_text_fraction: float
