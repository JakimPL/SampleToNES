from pydantic import BaseModel

from sampletones_application.layout.general import Padding
from sampletones_application.utils.palette import PaletteColor


class OrderLayout(BaseModel, extra="forbid", frozen=True):
    height: int
    position_column_width: int
    master_divider_height: int


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


class TempoLayout(BaseModel, extra="forbid", frozen=True):
    min: int
    max: int
    default: int


class SpeedLayout(BaseModel, extra="forbid", frozen=True):
    min: int
    max: int
    default: int


class SubcolumnWidths(BaseModel, extra="forbid", frozen=True):
    instrument: int
    transpose: int
    volume: int


class TrackerColors(BaseModel, extra="forbid", frozen=True):
    """The semantic text colours shared across every tracker view.

    One palette feeds the pattern grid, the order table, and the history detail so a
    concept keeps its colour everywhere: ``instrument`` (the note/sample reference,
    yellow like ``sample``), ``transpose``, ``volume``, ``sample``, the ``frame`` and
    ``row`` indices, and the ``order`` entries. Defining them once keeps the panels in
    step instead of each carrying its own copy.
    """

    instrument: PaletteColor
    transpose: PaletteColor
    volume: PaletteColor
    sample: PaletteColor
    frame: PaletteColor
    row: PaletteColor
    order: PaletteColor


class HistoryRoleColors(BaseModel, extra="forbid", frozen=True):
    """Colours for the history-detail token roles that the tracker does not already own.

    The instrument/transpose/volume, frame, row, and sample tokens draw from the
    shared :class:`TrackerColors` palette; only the roles unique to the detail line
    live here.
    """

    channel: PaletteColor
    value: PaletteColor
    separator: PaletteColor


class TrackerLayout(BaseModel, extra="forbid", frozen=True):
    rows: int
    row_height: int
    page_size: int
    subcolumn_widths: SubcolumnWidths
    channel_column_tint: float


class ChannelColors(BaseModel, extra="forbid", frozen=True):
    """Per-channel identity colours shared by the order table and the tracker grid.

    The order table paints each channel's row label in its colour; the tracker grid
    tints each channel's column background with the same colour at a low alpha, so a
    channel keeps one identity across both views.
    """

    pulse1: PaletteColor
    pulse2: PaletteColor
    triangle: PaletteColor
    noise: PaletteColor


class OrderColors(BaseModel, extra="forbid", frozen=True):
    """Colours specific to the order table: the row-label column, the master row and
    the divider below it, and the per-column highlights for the current and playing
    positions.
    """

    label: PaletteColor
    master: PaletteColor
    master_divider: PaletteColor
    column_current: PaletteColor
    column_playing: PaletteColor


class SampleColors(BaseModel, extra="forbid", frozen=True):
    """Colours marking the tracker's sample column and the divider beside it."""

    column: PaletteColor
    divider: PaletteColor


class HistoryColors(BaseModel, extra="forbid", frozen=True):
    """Colours for the history detail: the dimmed tint of future (redoable) entries
    and the per-role token palette.
    """

    future: PaletteColor
    roles: HistoryRoleColors


class SequencerColors(BaseModel, extra="forbid", frozen=True):
    pattern_highlight: PaletteColor
    cell_cursor: PaletteColor
    cursor_row: PaletteColor
    playback_row: PaletteColor
    label: PaletteColor
    order: OrderColors
    sample: SampleColors
    history: HistoryColors
    text: TrackerColors
    channels: ChannelColors


class HistoryLayout(BaseModel, extra="forbid", frozen=True):
    height: int
    selectable_column_weight: float
    max_rendered_entries: int


class SequencerLayout(BaseModel, extra="forbid", frozen=True):
    cell_padding: Padding
    order: OrderLayout
    table_cells: SequencerTableCells
    tempo: TempoLayout
    speed: SpeedLayout
    tracker: TrackerLayout
    history: HistoryLayout
    colors: SequencerColors
