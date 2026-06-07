from typing import Final, Optional, Tuple

from sampletones_application.ui.panels.sequencer.input.cursor import TrackerCursor
from sampletones_application.ui.panels.sequencer.input.subcolumn import SubColumn
from sampletones_core.constants.enums import GeneratorName

COLUMNS: Final[Tuple[Optional[GeneratorName], ...]] = (None,) + tuple(GeneratorName.items())
SUBCOLUMNS: Final[Tuple[SubColumn, ...]] = tuple(SubColumn)


def flat_index(generator: Optional[GeneratorName], subcolumn: SubColumn) -> int:
    return COLUMNS.index(generator) * len(SUBCOLUMNS) + SUBCOLUMNS.index(subcolumn)


def from_flat(row: int, index: int) -> TrackerCursor:
    index %= len(COLUMNS) * len(SUBCOLUMNS)
    column, sub = divmod(index, len(SUBCOLUMNS))
    return TrackerCursor(row, COLUMNS[column], SUBCOLUMNS[sub])


def tracker_table_column(generator: Optional[GeneratorName]) -> int:
    # +2 accounts for the leading spacer and row-number columns in the DPG tracker table
    return COLUMNS.index(generator) + 2
