from __future__ import annotations

from typing import Final, Optional, Tuple

from pydantic.dataclasses import dataclass

from sampletones_application.constants.sequencer import CHANNEL_AXIS
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import GeneratorName

SUBCOLUMNS: Final[Tuple[SubColumn, ...]] = tuple(SubColumn)
SLOT_COUNT: Final[int] = len(CHANNEL_AXIS) * len(SUBCOLUMNS)


@dataclass(frozen=True)
class TrackerSlot:
    """One addressable cell of the tracker grid: a column paired with a subcolumn.

    The grid lays the sample column and the four channels out along
    :data:`CHANNEL_AXIS`, each holding the same :data:`SUBCOLUMNS`, so a slot reads
    equally as that pair and as a single index into the flattened axis. Both
    readings are load-bearing: navigation and range selection walk the flat index,
    while an edit addresses the column and the subcolumn it lands in.
    """

    generator: Optional[GeneratorName]
    subcolumn: SubColumn

    @property
    def flat_index(self) -> int:
        return column_slot_base(self.generator) + SUBCOLUMNS.index(self.subcolumn)


def column_slot_base(generator: Optional[GeneratorName]) -> int:
    """The flat index of ``generator``'s first subcolumn.

    Every base is a multiple of ``len(SUBCOLUMNS)``, which is what keeps an offset
    measured from one column's base addressing the same kind of subcolumn at any
    other column it is replayed against.
    """
    return CHANNEL_AXIS.index(generator) * len(SUBCOLUMNS)


def slot_from_flat(index: int) -> TrackerSlot:
    """Reads a flat index back as the column and subcolumn it addresses.

    The mapping is exact over the axis, so a caller that walks off either end is
    asking for a slot the grid has no cell for: navigation wraps its index before
    calling, and a range selection clips to the axis.

    Raises:
        IndexError: if ``index`` lies outside ``0`` up to :data:`SLOT_COUNT`.
    """
    if not 0 <= index < SLOT_COUNT:
        raise IndexError(f"Tracker slot index out of range: {index}")

    column, subcolumn = divmod(index, len(SUBCOLUMNS))
    return TrackerSlot(CHANNEL_AXIS[column], SUBCOLUMNS[subcolumn])
