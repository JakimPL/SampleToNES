from pydantic import BaseModel

from sampletones_application.layout.tabs.sequencer.tracker.subcolumn import SubcolumnWidths


class TrackerLayout(BaseModel, extra="forbid", frozen=True):
    """The tracker's row counts, cell sizes and tint strengths.

    The grouping the rows are tinted by is the project's own metre, read from its highlights,
    so this model carries the geometry alone.

    A row states its height rather than growing to the text in it, because the grid's tints are
    drawn by the cells: a cell that stands exactly as tall as its row lets a selection, a hover
    and the cursor cover the row edge to edge.
    """

    rows: int
    page_size: int
    row_height: int
    header_height: int
    subcolumn_widths: SubcolumnWidths
    channel_column_tint: float
    muted_text_fraction: float
