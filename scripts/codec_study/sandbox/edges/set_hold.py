from typing import Final

from codec_study.sandbox.context import PlaneContext
from codec_study.sandbox.edges.generator import EdgeGenerator, offered_lengths
from codec_study.sandbox.shortest import Shortest
from codec_study.sandbox.tokens import SetHold, StudyToken

LEAST_SET_HOLD_TICKS: Final[int] = 2


def set_hold_edges(*, every_length: bool) -> EdgeGenerator:
    """Set-holds (H3): one token taking a value and keeping it for a run of ticks.

    The token names its value, so it starts anywhere a run does, the stream's first tick and a
    loop entry included. A run of one tick is a literal's, which costs the same and carries
    more.

    Args:
        every_length: Whether a set-hold of every length is offered beside the longest one.

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
        del holdable
        index = context.index
        longest = min(context.costs.operands, index.runs[position], reach)
        if longest < LEAST_SET_HOLD_TICKS:
            return

        value = index.plane[position]
        cost = shortest.costs[position] + context.costs.set_hold
        for ticks in offered_lengths(longest, least=LEAST_SET_HOLD_TICKS, every=every_length):
            if shortest.improves(position + ticks, cost):
                shortest.relax(position, position + ticks, cost, SetHold(value=value, ticks=ticks))

    return relax
