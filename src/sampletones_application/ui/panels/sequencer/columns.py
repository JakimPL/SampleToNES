from typing import Final, Optional, Tuple

from sampletones_application.layout.sequencer import ChannelColors
from sampletones_application.ui.panels.sequencer.input.cursor import TrackerCursor
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import GeneratorName
from sampletones_shared.types.application import ColorRGBA

COLUMNS: Final[Tuple[Optional[GeneratorName], ...]] = (None,) + tuple(GeneratorName.items())
SUBCOLUMNS: Final[Tuple[SubColumn, ...]] = tuple(SubColumn)

_LEADING_TABLE_COLUMNS: Final[int] = 2
SAMPLE_TABLE_COLUMN: Final[int] = _LEADING_TABLE_COLUMNS
DIVIDER_TABLE_COLUMN: Final[int] = SAMPLE_TABLE_COLUMN + 1
_FIRST_CHANNEL_TABLE_COLUMN: Final[int] = DIVIDER_TABLE_COLUMN + 1


def flat_index(generator: Optional[GeneratorName], subcolumn: SubColumn) -> int:
    return COLUMNS.index(generator) * len(SUBCOLUMNS) + SUBCOLUMNS.index(subcolumn)


def from_flat(row: int, index: int) -> TrackerCursor:
    index %= len(COLUMNS) * len(SUBCOLUMNS)
    column, sub = divmod(index, len(SUBCOLUMNS))
    return TrackerCursor(row, COLUMNS[column], SUBCOLUMNS[sub])


def channel_color(colors: ChannelColors, generator: GeneratorName) -> ColorRGBA:
    match generator:
        case GeneratorName.PULSE1:
            return colors.pulse1
        case GeneratorName.PULSE2:
            return colors.pulse2
        case GeneratorName.TRIANGLE:
            return colors.triangle
        case GeneratorName.NOISE:
            return colors.noise


def tracker_table_column(generator: Optional[GeneratorName]) -> int:
    """Maps a logical column to its DPG table column index.

    The visual divider between the sample column and the channels occupies a table
    column of its own, so the channels sit one slot further right than their
    logical position. The divider is purely visual, so :data:`COLUMNS` covers only
    the cursor-addressable columns.
    """
    if generator is None:
        return SAMPLE_TABLE_COLUMN

    return _FIRST_CHANNEL_TABLE_COLUMN + GeneratorName.items().index(generator)
