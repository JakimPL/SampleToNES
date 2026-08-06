from pydantic import BaseModel

from sampletones_application.utils.palette.color import PaletteColor


class TrackerColors(BaseModel, extra="forbid", frozen=True):
    """The semantic text colours shared across every tracker view.

    One palette feeds the pattern grid, the order table, and the history detail so a
    concept keeps its colour everywhere: ``instrument`` (the note/sample reference,
    yellow like ``sample``), ``transpose``, ``volume``, ``sample``, the ``frame`` and
    ``row`` indices, and the ``order`` entries. Defining them once keeps every panel in
    step.
    """

    instrument: PaletteColor
    transpose: PaletteColor
    volume: PaletteColor
    sample: PaletteColor
    frame: PaletteColor
    row: PaletteColor
    order: PaletteColor


class HistoryRoleColors(BaseModel, extra="forbid", frozen=True):
    """Colours for the history-detail token roles unique to the detail line.

    The instrument/transpose/volume, frame, row, and sample tokens draw from the
    shared :class:`TrackerColors` palette; only the roles unique to the detail line
    live here.
    """

    channel: PaletteColor
    value: PaletteColor
    separator: PaletteColor


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


class HeaderColors(BaseModel, extra="forbid", frozen=True):
    """Colours the tracker's clickable column header takes.

    ``background`` is the band the header row sits in, the shade a table header carries;
    ``hovered`` and ``active`` are the washes a header label takes under the pointer and while
    it is held, which is how the label shows it answers to a click.
    """

    background: PaletteColor
    hovered: PaletteColor
    active: PaletteColor


class MutedColors(BaseModel, extra="forbid", frozen=True):
    """Colours marking a channel the song player silences.

    ``background`` is the neutral shade the channel takes in place of its identity tint —
    down its column in the tracker, along its row in the order table — so the channel
    recedes as a whole; ``text`` is the shade its name takes.
    """

    background: PaletteColor
    text: PaletteColor


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
    header: HeaderColors
    muted: MutedColors
    history: HistoryColors
    text: TrackerColors
    channels: ChannelColors
