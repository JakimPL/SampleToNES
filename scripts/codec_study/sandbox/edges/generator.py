from typing import Iterable, Protocol

from codec_study.sandbox.context import PlaneContext
from codec_study.sandbox.shortest import Shortest
from codec_study.sandbox.tokens import StudyToken


class EdgeGenerator(Protocol):
    """Offers every token of one kind that may start at a tick of a plane."""

    def __call__(
        self,
        context: PlaneContext,
        shortest: Shortest[StudyToken],
        position: int,
        reach: int,
        *,
        holdable: bool,
    ) -> None:
        """Relaxes the edges of the tokens starting at ``position``.

        Args:
            context: The plane and the terms the grammar reads it on.
            shortest: The search the edges join.
            position: The tick the tokens start on.
            reach: The most ticks a token may cover from there.
            holdable: Whether a token may keep the value the plane holds as the tick is reached.
        """


def offered_lengths(
    longest: int,
    *,
    least: int,
    every: bool,
) -> Iterable[int]:
    """The lengths a token kind is offered at from one tick.

    The codec as it stands offers the longest token alone, and a grammar asking for every
    length offers each one from ``least`` up to it.

    Args:
        longest: The most ticks the token may cover.
        least: The fewest ticks a token of the kind covers.
        every: Whether every length is offered.

    Returns:
        Iterable[int]: The lengths, the longest one last.
    """
    if every:
        return range(least, longest + 1)

    return (longest,)
