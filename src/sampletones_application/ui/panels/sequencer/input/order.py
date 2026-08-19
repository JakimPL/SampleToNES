from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Optional, Tuple

from sampletones_application.constants.sequencer import CHANNEL_AXIS
from sampletones_application.ui.panels.sequencer.input.state import GridInputState
from sampletones_application.view_model.sequencer.region import OrderRegion
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.constants.general import HEXADECIMAL_BASE

INDEX_DIGITS: Final[int] = 2


@dataclass(frozen=True)
class OrderCursor:
    channel: Optional[ChannelName]
    position: int


def _parse(pending: str) -> Optional[int]:
    try:
        return int(pending, HEXADECIMAL_BASE)
    except ValueError:
        return None


@dataclass(frozen=True)
class OrderInputState(GridInputState[OrderCursor, OrderRegion]):
    """Edit cursor, pending hex entry and selection anchor for the order table.

    The order has no subcolumns, so a cell holds a single pattern index; typing
    accumulates :data:`INDEX_DIGITS` hex digits and then commits the parsed index.
    Navigation moves along positions (columns) or channels/master (rows).
    """

    def _region_between(
        self,
        first: OrderCursor,
        second: OrderCursor,
    ) -> OrderRegion:
        first_row = CHANNEL_AXIS.index(first.channel)
        second_row = CHANNEL_AXIS.index(second.channel)
        return OrderRegion(
            first_row=min(first_row, second_row),
            last_row=max(first_row, second_row),
            first_position=min(first.position, second.position),
            last_position=max(first.position, second.position),
        )

    def _covers(self, region: OrderRegion, cell: OrderCursor) -> bool:
        return region.covers(cell.channel, cell.position)

    def select_all(self, position_count: int) -> OrderInputState:
        """Selects the whole order: every channel row, across every position it holds."""
        return self._select_rows(CHANNEL_AXIS[0], CHANNEL_AXIS[-1], position_count)

    def select_row(
        self,
        cell: OrderCursor,
        position_count: int,
    ) -> OrderInputState:
        """Selects the row ``cell`` stands in: that channel, across every position.

        The master row is an ordinary member of the axis here, so selecting it selects a row the
        way selecting a channel does.
        """
        return self._select_rows(cell.channel, cell.channel, position_count)

    def _select_rows(
        self,
        first_generator: Optional[ChannelName],
        last_generator: Optional[ChannelName],
        position_count: int,
    ) -> OrderInputState:
        """Selects a run of rows across the whole order, the cursor landing on its far corner."""
        if position_count == 0:
            return self

        return self.select_between(
            OrderCursor(first_generator, 0),
            OrderCursor(last_generator, position_count - 1),
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
        return self.extend_to(OrderCursor(self.cursor.channel, new_position))

    def extend_channel(self, value: int) -> OrderInputState:
        """Carries the selection's moving end across the channel axis, stopping at either end.

        A selection covers a run of the table, so the walk stops at the master row and at the last
        channel rather than wrapping around the way plain navigation does.
        """
        if self.cursor is None:
            return self

        current = CHANNEL_AXIS.index(self.cursor.channel)
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
            cursor=OrderCursor(self.cursor.channel, new_position),
            pending="",
        )

    def navigate_channel(self, value: int) -> OrderInputState:
        if self.cursor is None:
            return self

        current = CHANNEL_AXIS.index(self.cursor.channel)
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

    def commit_partial(self) -> Tuple[OrderInputState, Optional[int]]:
        if not self.pending or self.cursor is None:
            return self, None

        return self.reset_pending(), _parse(self.pending.zfill(INDEX_DIGITS))
