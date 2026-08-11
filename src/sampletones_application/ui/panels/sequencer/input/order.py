from __future__ import annotations

from typing import Final, Optional, Tuple

from pydantic.dataclasses import dataclass

from sampletones_application.constants.sequencer import CHANNEL_AXIS
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
    """Edit cursor and pending hex entry for the order table.

    The order has no subcolumns, so a cell holds a single pattern index; typing
    accumulates :data:`INDEX_DIGITS` hex digits and then commits the parsed index.
    Navigation moves along positions (columns) or channels/master (rows).
    """

    cursor: Optional[OrderCursor] = None
    pending: str = ""

    def reset_pending(self) -> OrderInputState:
        return OrderInputState(cursor=self.cursor, pending="")

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

        return self.reset_pending(), _parse(pending)

    def commit_partial(self) -> Tuple[OrderInputState, Optional[int]]:
        if not self.pending or self.cursor is None:
            return self, None

        return self.reset_pending(), _parse(self.pending.zfill(INDEX_DIGITS))

    def cancel(self) -> OrderInputState:
        return self.reset_pending()
