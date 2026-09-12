from typing import Final

from codec_study.sandbox.context import PlaneContext
from codec_study.sandbox.edges.generator import EdgeGenerator, offered_lengths
from codec_study.sandbox.shortest import Shortest
from codec_study.sandbox.tokens import Hold, StudyToken, WideHold
from sampletones_player.specification.compression import MAX_HOLD_TICKS

LEAST_HOLD_TICKS: Final[int] = 1
LEAST_WIDE_BLOCKS: Final[int] = 1


def hold_edges(*, every_length: bool) -> EdgeGenerator:
    """Holds, as the codec offers them: over the value the plane holds as the tick is reached.

    Args:
        every_length: Whether a hold of every length is offered beside the longest one.

    Returns:
        EdgeGenerator: The generator.
    """

    def relax(
        context: PlaneContext,
        shortest: Shortest[StudyToken],
        position: int,
        reach: int,
        *,
        holdable: bool,
    ) -> None:
        index = context.index
        if not holdable or index.plane[position] != context.value_before(position):
            return

        longest = min(MAX_HOLD_TICKS, index.runs[position], reach)
        cost = shortest.costs[position] + context.costs.hold
        for ticks in offered_lengths(longest, least=LEAST_HOLD_TICKS, every=every_length):
            if shortest.improves(position + ticks, cost):
                shortest.relax(position, position + ticks, cost, Hold(ticks=ticks))

    return relax


def wide_hold_edges(*, every_length: bool) -> EdgeGenerator:
    """Wide holds (H1): whole blocks of a plain hold's longest reach, counted by one token.

    A wide hold rides the free escape, so it counts as many blocks as the escape has operand
    values, and a run shorter than a block is left to a plain hold.

    Args:
        every_length: Whether a wide hold of every block count is offered beside the longest.

    Returns:
        EdgeGenerator: The generator.
    """

    def relax(
        context: PlaneContext,
        shortest: Shortest[StudyToken],
        position: int,
        reach: int,
        *,
        holdable: bool,
    ) -> None:
        index = context.index
        if not holdable or index.plane[position] != context.value_before(position):
            return

        longest = min(context.costs.operands, index.runs[position] // MAX_HOLD_TICKS, reach // MAX_HOLD_TICKS)
        if longest < LEAST_WIDE_BLOCKS:
            return

        cost = shortest.costs[position] + context.costs.wide_hold
        for blocks in offered_lengths(longest, least=LEAST_WIDE_BLOCKS, every=every_length):
            end = position + blocks * MAX_HOLD_TICKS
            if shortest.improves(end, cost):
                shortest.relax(position, end, cost, WideHold(blocks=blocks))

    return relax
