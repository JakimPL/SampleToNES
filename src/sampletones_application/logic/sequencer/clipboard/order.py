from typing import Dict, Final, List, Optional

from sampletones_application.constants.sequencer import CHANNEL_AXIS
from sampletones_application.logic.sequencer.order.block import BlockKey, OrderBlock
from sampletones_application.view_model.sequencer.region import OrderRegion
from sampletones_core.utils.display import display_id

from .fields import (
    FieldReading,
    read_hexadecimal,
    read_placeholder,
    state_mixed,
    store_reading,
)
from .header import BlockShape, parse_header, state_header

ORDER_GRID: Final[str] = "order"
POSITION_KEY: Final[str] = "positions"
ENTRY_WIDTH: Final[int] = len(display_id(None))


class OrderBlockText:
    """States an order block as the lines the table prints, and reads the same form back.

    One line per channel row, positions running across it, every field carrying what the table
    shows in its cell: a pattern index, the dots of a silent slot, or the marks a master cell
    fills its field with where the channels beneath it disagree.
    """

    def state(self, block: OrderBlock, region: OrderRegion) -> str:
        """The text a copy puts on the system clipboard, the region supplying the shape.

        The region is what states the positions the block stands on, since a mixed cell leaves
        its key out and a block alone therefore names less than the rectangle it came from.
        """
        shape = BlockShape(
            rows=len(region.rows),
            first=region.first_position,
            last=region.last_position,
        )
        lines = [state_header(grid=ORDER_GRID, span_key=POSITION_KEY, shape=shape)]
        lines.extend(self._state_row(block, shape, row_offset) for row_offset in range(shape.rows))
        return "\n".join(lines)

    def parse(self, text: str) -> Optional[OrderBlock]:
        """The block a text states, present while it is one this table writes.

        Text naming another grid, declaring a shape its lines do not fill, or carrying a field
        the form has no reading for states no block, so the slot the order copied into stands.
        """
        lines = text.strip().splitlines()
        if not lines:
            return None

        shape = parse_header(lines[0], grid=ORDER_GRID, span_key=POSITION_KEY)
        if shape is None or shape.rows > len(CHANNEL_AXIS) or len(lines) != shape.rows + 1:
            return None

        return self._read_rows(lines[1:], shape)

    def _state_row(
        self,
        block: OrderBlock,
        shape: BlockShape,
        row_offset: int,
    ) -> str:
        """One row of the block, its fields standing in the order the positions run."""
        return " ".join(
            self._state_entry(
                block,
                (row_offset, position_offset),
            )
            for position_offset in range(shape.width)
        )

    @staticmethod
    def _state_entry(block: OrderBlock, key: BlockKey) -> str:
        if key not in block.entries:
            return state_mixed(ENTRY_WIDTH)

        return display_id(block.entries[key])

    def _read_rows(
        self,
        lines: List[str],
        shape: BlockShape,
    ) -> Optional[OrderBlock]:
        entries: Dict[BlockKey, Optional[int]] = {}
        for row_offset, line in enumerate(lines):
            fields = line.split()
            if len(fields) != shape.width:
                return None

            for position_offset, field in enumerate(fields):
                key = (row_offset, position_offset)
                if not store_reading(entries, key, self._read_entry(field)):
                    return None

        return OrderBlock(entries=entries)

    @staticmethod
    def _read_entry(field: str) -> Optional[FieldReading[int]]:
        """The pattern a field names, present while it states an index or one of the two marks."""
        placeholder: Optional[FieldReading[int]] = read_placeholder(field)
        if placeholder is not None:
            return placeholder

        pattern_index = read_hexadecimal(field)
        if pattern_index is None:
            return None

        return FieldReading.of(pattern_index)
