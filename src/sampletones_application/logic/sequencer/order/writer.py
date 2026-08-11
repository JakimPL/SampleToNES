from typing import List, Optional, Tuple

from sampletones_application.constants.sequencer import CHANNEL_AXIS
from sampletones_application.view_model.sequencer.region import OrderCell, OrderRegion

from .block import OrderBlock
from .order import SequencerOrderLogic

OrderWrite = Tuple[int, int, Optional[int]]


class OrderBlockWriter:
    """Replays a block into the order table, and empties the cells a region covers.

    Every cell reaches the table through the single-entry edit that already governs it, so a paste
    lands exactly the writes a reader typing the same indices by hand would make, master row
    included.
    """

    def __init__(self, order_logic: SequencerOrderLogic) -> None:
        self._order = order_logic

    def write(self, block: OrderBlock, cell: OrderCell) -> None:
        """Writes a block anchored at a cell, the order growing to hold what it reaches past its end.

        The whole block is resolved before any of it lands, so the frames a write needs exist by the
        time it reaches them and the growth belongs to the same gesture as the writes it carries.
        """
        writes = self._resolve(block, cell)
        self._grow(writes)
        for row, position, pattern_index in writes:
            self._order.write_entry(CHANNEL_AXIS[row], position, pattern_index)

    def clear(self, region: OrderRegion) -> None:
        """Silences every cell a region covers, each by the rule its own row follows.

        The order keeps its length, so emptying the frames at its end leaves them standing as
        silent ones rather than taking positions away from the arrangement.
        """
        for generator in region.generators:
            for position in region.positions:
                self._order.write_entry(generator, position, None)

    def _resolve(self, block: OrderBlock, cell: OrderCell) -> List[OrderWrite]:
        """Where each of a block's entries lands, in the reading order they are written in.

        Keys are taken in reading order, so a position's master row is written before the channels
        beneath it and the more specific write is the one that stands. A row past the last channel
        is left out, which clips a block at the bottom edge rather than wrapping it round to the
        master row.
        """
        base_row = CHANNEL_AXIS.index(cell.generator)
        return [
            (base_row + row_offset, cell.position + position_offset, pattern_index)
            for (row_offset, position_offset), pattern_index in sorted(block.entries.items())
            if base_row + row_offset < len(CHANNEL_AXIS)
        ]

    def _grow(self, writes: List[OrderWrite]) -> None:
        """Appends the frames a block reaches past the order's end.

        The order grows to the last position a write actually lands at, so a column the block says
        nothing about appends no frame while one it silences appends the frame it silences.
        """
        positions = [position for _, position, _ in writes]
        if not positions:
            return

        required = max(positions) + 1
        for _ in range(required - self._order.position_count()):
            self._order.append_frame()
