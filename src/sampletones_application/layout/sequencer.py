from pydantic import BaseModel

from sampletones_application.layout.general import Padding
from sampletones_application.utils.color import RGBA


class OrderLayout(BaseModel, frozen=True):
    height: int
    position_column_width: int
    master_divider_height: int


class InstrumentColumnWidths(BaseModel, frozen=True):
    """Widths of the three sub-columns that make up an instrument row: its id, its
    name, and its loop marker. They only mean anything as a set, so they live together.
    """

    id: int
    name: int
    loop: int


class SequencerTableCells(BaseModel, frozen=True):
    row: int
    sample: int
    divider: int
    generator: int
    instrument: InstrumentColumnWidths


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
    channel_column_tint: float


class ChannelColors(BaseModel, frozen=True):
    """Per-channel identity colours shared by the order table and the tracker grid.

    The order table paints each channel's row label in its colour; the tracker grid
    tints each channel's column background with the same colour at a low alpha, so a
    channel keeps one identity across both views.
    """

    pulse1: RGBA
    pulse2: RGBA
    triangle: RGBA
    noise: RGBA


class OrderColors(BaseModel, frozen=True):
    """Colours specific to the order table: the row-label column, the master row and
    the divider below it, and the per-column highlights for the current and playing
    positions.
    """

    label: RGBA
    master: RGBA
    master_divider: RGBA
    column_current: RGBA
    column_playing: RGBA


class SampleColors(BaseModel, frozen=True):
    """Colours marking the tracker's sample column and the divider beside it."""

    column: RGBA
    divider: RGBA


class HistoryColors(BaseModel, frozen=True):
    """Colours for the history detail: the dimmed tint of future (redoable) entries
    and the per-role token palette.
    """

    future: RGBA
    roles: HistoryRoleColors


class SequencerColors(BaseModel, frozen=True):
    pattern_highlight: RGBA
    cell_cursor: RGBA
    cursor_row: RGBA
    playback_row: RGBA
    label: RGBA
    order: OrderColors
    sample: SampleColors
    history: HistoryColors
    text: TrackerColors
    channels: ChannelColors


class HistoryLayout(BaseModel, frozen=True):
    height: int
    margin: int
    selectable_column_weight: float
    max_rendered_entries: int


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
