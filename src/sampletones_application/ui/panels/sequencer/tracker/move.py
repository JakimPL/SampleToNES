from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from sampletones_application.ui.panels.sequencer.input.tracker import TrackerCursor
from sampletones_core.constants.enums import ChannelName

CellPlace = Tuple[int, Optional[ChannelName]]


def cell_place(cursor: Optional[TrackerCursor]) -> Optional[CellPlace]:
    """The cell a cursor stands in, its row and its channel, or None for no cursor."""
    if cursor is None:
        return None

    return (cursor.row, cursor.channel)


@dataclass(frozen=True)
class CursorMove:
    """The painting a change of the cursor owes the grid: the cell it left and the cell it reached.

    Attributes:
        left: The cell the cursor stood in before, or None where it stood in none.
        reached: The cell the cursor stands in now, or None where it stands in none.
    """

    left: Optional[CellPlace]
    reached: Optional[CellPlace]

    def then(self, move: CursorMove) -> CursorMove:
        """This move carried on by ``move``: the cell first left and the cell last reached."""
        return CursorMove(left=self.left, reached=move.reached)
