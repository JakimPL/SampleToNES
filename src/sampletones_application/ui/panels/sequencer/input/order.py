from __future__ import annotations

from typing import Final, Optional, Tuple

from pydantic.dataclasses import dataclass

from sampletones_application.constants.sequencer import CHANNEL_AXIS
from sampletones_application.view_model.sequencer.region import OrderRegion
from sampletones_core.constants.enums import GeneratorName

INDEX_DIGITS: Final[int] = 2


@dataclass(frozen=True)
class OrderCursor:
    generator: Optional[GeneratorName]
    position: int


def _parse(pending: str) -> Optional[int]:
    try:
        return int(pending, 16)
    except ValueError:
        return None


@dataclass
class OrderInputState:
    """Edit cursor, pending hex entry and selection anchor for the order table.

    The order has no subcolumns, so a cell holds a single pattern index; typing
    accumulates :data:`INDEX_DIGITS` hex digits and then commits the parsed index.
    Navigation moves along positions (columns) or channels/master (rows). The anchor is where a
    range selection was started and the cursor is its other end, so the two together are the
    block a copy or a paste acts on.
    """

    cursor: Optional[OrderCursor] = None
    pending: str = ""
    anchor: Optional[OrderCursor] = None

    def reset_pending(self) -> OrderInputState:
        """Drops a partial entry, leaving the cursor and any selection where they stand.

        The anchor survives because this runs before every move, the extending ones included:
        each gesture then decides whether to hold the selection or collapse it.
        """
        return OrderInputState(cursor=self.cursor, pending="", anchor=self.anchor)

    def collapse(self) -> OrderInputState:
        """Drops the selection, leaving the cursor's own cell as the whole target."""
        return OrderInputState(cursor=self.cursor, pending=self.pending)

    @property
    def region(self) -> Optional[OrderRegion]:
        """The block a selection covers, once one has been started."""
        if self.cursor is None or self.anchor is None:
            return None

        anchor_row = CHANNEL_AXIS.index(self.anchor.generator)
        cursor_row = CHANNEL_AXIS.index(self.cursor.generator)
        return OrderRegion(
            first_row=min(anchor_row, cursor_row),
            last_row=max(anchor_row, cursor_row),
            first_position=min(self.anchor.position, self.cursor.position),
            last_position=max(self.anchor.position, self.cursor.position),
        )

    @property
    def target_region(self) -> Optional[OrderRegion]:
        """The region a block gesture acts on: the selection, or the cursor's own cell.

        A cursor with nothing selected stands on a block of one cell, so copying reaches the cell
        the reader is working in and needs no selection made first.
        """
        if self.region is not None:
            return self.region

        if self.cursor is None:
            return None

        row = CHANNEL_AXIS.index(self.cursor.generator)
        return OrderRegion(
            first_row=row,
            last_row=row,
            first_position=self.cursor.position,
            last_position=self.cursor.position,
        )

    def extend_to(self, cursor: OrderCursor) -> OrderInputState:
        """Carries the moving end of the selection to ``cursor``, anchoring it where it began.

        A selection that has not been started yet takes the cell the cursor stands on as its
        anchor, so the first extending gesture selects the cell it came from as well as the one
        it reaches.
        """
        return OrderInputState(
            cursor=cursor,
            pending="",
            anchor=self.anchor if self.anchor is not None else self.cursor,
        )

    def extend_position(
        self,
        value: int,
        position_count: int,
        absolute: bool = False,
    ) -> OrderInputState:
        """Carries the selection's moving end to another position of the same row."""
        if self.cursor is None or position_count == 0:
            return self

        new_position = value if absolute else self.cursor.position + value
        new_position = max(0, min(new_position, position_count - 1))
        return self.extend_to(OrderCursor(self.cursor.generator, new_position))

    def extend_channel(self, value: int) -> OrderInputState:
        """Carries the selection's moving end across the channel axis, stopping at either end.

        A selection covers a run of the table, so the walk stops at the master row and at the last
        channel rather than wrapping around the way plain navigation does.
        """
        if self.cursor is None:
            return self

        current = CHANNEL_AXIS.index(self.cursor.generator)
        row = max(0, min(current + value, len(CHANNEL_AXIS) - 1))
        return self.extend_to(OrderCursor(CHANNEL_AXIS[row], self.cursor.position))

    def navigate_position(
        self,
        value: int,
        position_count: int,
        absolute: bool = False,
    ) -> OrderInputState:
        if self.cursor is None or position_count == 0:
            return self

        new_position = value if absolute else self.cursor.position + value
        new_position = max(0, min(new_position, position_count - 1))
        return OrderInputState(
            cursor=OrderCursor(self.cursor.generator, new_position),
            pending="",
        )

    def navigate_channel(self, value: int) -> OrderInputState:
        if self.cursor is None:
            return self

        current = CHANNEL_AXIS.index(self.cursor.generator)
        new_generator = CHANNEL_AXIS[(current + value) % len(CHANNEL_AXIS)]
        return OrderInputState(
            cursor=OrderCursor(new_generator, self.cursor.position),
            pending="",
        )

    def type_char(self, char: str) -> Tuple[OrderInputState, Optional[int]]:
        if self.cursor is None:
            return self, None

        pending = self.pending + char
        if len(pending) < INDEX_DIGITS:
            return OrderInputState(cursor=self.cursor, pending=pending), None

        return self._after_entry(), _parse(pending)

    def _after_entry(self) -> OrderInputState:
        """The state a committed entry leaves: the cursor alone, nothing pending and nothing selected.

        Typing writes the one cell the cursor stands on, so it takes the selection down to that
        cell instead of leaving a range for the next gesture to act on.
        """
        return self.collapse().reset_pending()

    def commit_partial(self) -> Tuple[OrderInputState, Optional[int]]:
        if not self.pending or self.cursor is None:
            return self, None

        return self.reset_pending(), _parse(self.pending.zfill(INDEX_DIGITS))

    def cancel(self) -> OrderInputState:
        """Drops a partial entry and any selection, which is what Escape asks of the table."""
        return self.collapse().reset_pending()
