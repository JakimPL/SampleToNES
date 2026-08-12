from dataclasses import dataclass

from sampletones_application.ui.panels.sequencer.input.order import OrderCursor
from sampletones_application.ui.panels.sequencer.input.tracker import TrackerCursor
from sampletones_application.view_model.sequencer.region import (
    OrderCell,
    OrderRegion,
    TrackerCell,
    TrackerRegion,
)


@dataclass(frozen=True)
class TrackerTarget:
    """The tracker cell a set of actions was raised on, and the block those actions act on.

    Both are needed at once: the block decides what the clipboard actions cover, while the cell
    decides where a pasted block lands and which row and channel the cell-level actions reach.
    A target keeps the pair together, so a builder handed one prints a whole action set and a key
    press handed one reaches the same block the menus would.
    """

    cell: TrackerCursor
    region: TrackerRegion

    @property
    def anchor(self) -> TrackerCell:
        """The cell a pasted block is written from, which is the target's own row and column.

        A block carries the subcolumn offsets it was read at, so the anchor names a row and a
        column and leaves the rest to the block.
        """
        return TrackerCell(
            row=self.cell.row,
            generator=self.cell.generator,
        )


@dataclass(frozen=True)
class OrderTarget:
    """The order cell a set of actions was raised on, and the block those actions act on.

    Both are needed at once: the block decides what the clipboard actions cover, while the cell
    decides where a pasted block lands and which frame the frame actions reach.
    """

    cell: OrderCursor
    region: OrderRegion

    @property
    def anchor(self) -> OrderCell:
        """The cell a pasted block is written from, which is the target's own channel row and
        position."""
        return OrderCell(
            generator=self.cell.generator,
            position=self.cell.position,
        )
