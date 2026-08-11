from typing import Dict, Optional

from sampletones_application.view_model.sequencer.region import OrderRegion
from sampletones_core.constants.enums import GeneratorName
from sampletones_shared.utils.agreement import Agreement

from .block import BlockKey, OrderBlock
from .order import SequencerOrderLogic


class OrderBlockReader:
    """Reads a selected region of the order table into a block a paste can replay.

    The block is anchored at the cell the region begins in, so it carries offsets rather than
    table coordinates and lands wherever it is written.
    """

    def __init__(self, order_logic: SequencerOrderLogic) -> None:
        self._order = order_logic

    def read(self, region: OrderRegion) -> OrderBlock:
        """Takes the pattern indices a region covers, keyed by the offsets they stand at.

        A cell holding an index keeps it, a silent one keeps its silence, and a master cell whose
        channels disagree leaves its key out — which carries the table's mixed reading over as a
        value the paste passes by.
        """
        entries: Dict[BlockKey, Optional[int]] = {}
        for row_offset, generator in enumerate(region.generators):
            for position_offset, position in enumerate(region.positions):
                agreement = self._agree(generator, position)
                if agreement.is_unanimous:
                    entries[(row_offset, position_offset)] = agreement.value

        return OrderBlock(
            row_count=region.row_count,
            position_count=region.position_count,
            entries=entries,
        )

    def _agree(
        self,
        generator: Optional[GeneratorName],
        position: int,
    ) -> Agreement[Optional[int]]:
        """What a row holds at a position: a channel's own index, or the one its channels share.

        A channel row answers for itself, so it is a group of one and always agrees. The master row
        answers for every channel, which is the group its display summarises too, so a block states
        about a cell exactly what the table it came from shows there.
        """
        if generator is not None:
            return Agreement.collapse([self._order.entry(generator, position)])

        return Agreement.collapse(self._order.entry(channel, position) for channel in GeneratorName.items())
