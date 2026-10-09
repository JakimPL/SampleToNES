from collections import deque
from typing import Deque, Sequence


class LiteralWindow:
    """The tick a literal reaching the tick under consideration is cheapest to start from.

    A literal costs its opcode and its bytes alike whatever its length, so the start worth taking
    is the one whose own cost, set against how far back it sits, is least — and a start beaten
    by a later one is beaten for good. Keeping the starts in that order leaves the best of them
    at the front, which is what lets one pass over a plane price every literal in it.
    """

    def __init__(self, costs: Sequence[int]) -> None:
        self._costs = costs
        self._starts: Deque[int] = deque()

    def cheapest(self, position: int, earliest: int) -> int:
        """The tick the cheapest literal ending at ``position`` starts on.

        The tick before ``position`` joins the window as a start of its own, the starts it has
        beaten leave it, and so do the ones that have fallen out of reach.

        Args:
            position: The tick the literal ends at.
            earliest: The earliest tick that literal may start on.

        Returns:
            int: The tick the cheapest literal starts on.
        """
        starts = self._starts
        costs = self._costs
        start = position - 1
        key = costs[start] - start
        while starts and costs[starts[-1]] - starts[-1] >= key:
            starts.pop()

        starts.append(start)
        while starts[0] < earliest:
            starts.popleft()

        return starts[0]
