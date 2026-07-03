from pydantic import BaseModel

from sampletones_application.layout.general import Padding
from sampletones_application.utils.color import RGBA


class OrderLayout(BaseModel, frozen=True):
    height: int
    position_column_width: int
    master_divider_height: int


class SequencerTableCells(BaseModel, frozen=True):
    row: int
    sample: int
    divider: int
    generator: int
    instrument_id: int
    instrument_name: int
    instrument_loop: int


class TempoLayout(BaseModel, frozen=True):
    min: int
    max: int
    default: int


class SpeedLayout(BaseModel, frozen=True):
    min: int
    max: int
    default: int


class SubcolumnWidths(BaseModel, frozen=True):
    instrument: int
    transpose: int
    volume: int


class TrackerColors(BaseModel, frozen=True):
    """The semantic text colours shared across every tracker view.

    One palette feeds the pattern grid, the order table, and the history detail so a
    concept keeps its colour everywhere: ``instrument`` (the note/sample reference,
    yellow like ``sample``), ``transpose``, ``volume``, ``sample``, the ``frame`` and
    ``row`` indices, and the ``order`` entries. Defining them once keeps the panels in
    step instead of each carrying its own copy.
    """

    instrument: RGBA
    transpose: RGBA
    volume: RGBA
    sample: RGBA
    frame: RGBA
    row: RGBA
    order: RGBA


class HistoryRoleColors(BaseModel, frozen=True):
    """Colours for the history-detail token roles that the tracker does not already own.

    The instrument/transpose/volume, frame, row, and sample tokens draw from the
    shared :class:`TrackerColors` palette; only the roles unique to the detail line
    live here.
    """

    channel: RGBA
    value: RGBA
    separator: RGBA


class TrackerLayout(BaseModel, frozen=True):
    rows: int
    row_height: int
    page_size: int
    subcolumn_widths: SubcolumnWidths


class SequencerColors(BaseModel, frozen=True):
    pattern_highlight: RGBA
    cell_cursor: RGBA
    cursor_row: RGBA
    sample_column: RGBA
    sample_divider: RGBA
    order_label: RGBA
    order_master: RGBA
    order_master_divider: RGBA
    order_column: RGBA
    order_column_alternate: RGBA
    order_column_current: RGBA
    order_column_playing: RGBA
    playback_row: RGBA
    history_future: RGBA
    history_roles: HistoryRoleColors
    text: TrackerColors


class HistoryLayout(BaseModel, frozen=True):
    height: int
    margin: int
    selectable_column_weight: float


class SequencerLayout(BaseModel, frozen=True):
    samples_panel_width: int
    cell_padding: Padding
    order: OrderLayout
    table_cells: SequencerTableCells
    tempo: TempoLayout
    speed: SpeedLayout
    tracker: TrackerLayout
    history: HistoryLayout
    colors: SequencerColors
