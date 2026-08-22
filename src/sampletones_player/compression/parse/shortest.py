from __future__ import annotations

from dataclasses import dataclass
from typing import Final, List, Optional, Tuple

from sampletones_player.compression.tokens.types import TokenUnion

UNREACHED: Final[int] = -1


@dataclass
class Shortest:
    """The cheapest way found so far of reaching each tick of a plane.

    Every token is an edge from the tick it starts on to the tick after the ones it covers, and
    its cost is the bytes it takes, so the cheapest path across the plane is its encoding. Each
    tick remembers what it cost to reach and the token that reached it, which is what lets the
    tokens be read back once the far end is settled.

    Attributes:
        costs: The bytes reaching each tick takes, ticks not yet reached holding ``UNREACHED``.
        origins: The tick each one was reached from.
        tokens: The token each tick was reached by.
    """

    costs: List[int]
    origins: List[int]
    tokens: List[Optional[TokenUnion]]

    @classmethod
    def across(cls, ticks: int) -> Shortest:
        """Opens a search over a plane of ``ticks`` ticks, its first tick free to reach."""
        return cls(
            costs=[0] + [UNREACHED] * ticks,
            origins=[0] * (ticks + 1),
            tokens=[None] * (ticks + 1),
        )

    def improves(self, end: int, cost: int) -> bool:
        """Whether reaching ``end`` for ``cost`` beats what it has been reached for so far."""
        return self.costs[end] == UNREACHED or cost < self.costs[end]

    def relax(
        self,
        start: int,
        end: int,
        cost: int,
        token: TokenUnion,
    ) -> None:
        """Takes a token as the way to reach ``end`` where it is the cheapest one found.

        Args:
            start: The tick the token starts on.
            end: The tick following the ones the token covers.
            cost: The bytes reaching ``end`` through this token takes.
            token: The token covering the ticks between the two.
        """
        if self.costs[end] != UNREACHED and self.costs[end] <= cost:
            return

        self.costs[end] = cost
        self.origins[end] = start
        self.tokens[end] = token

    def walk(self, ticks: int) -> Tuple[TokenUnion, ...]:
        """Reads the tokens of the cheapest path back from ``ticks`` to the plane's first tick.

        Args:
            ticks: The tick the path ends at, which is the ticks the plane covers.

        Returns:
            Tuple[TokenUnion, ...]: The tokens, in the order they are read.

        Raises:
            ValueError: If a tick along the path was never reached.
        """
        read: List[TokenUnion] = []
        position = ticks
        while position > 0:
            token = self.tokens[position]
            if token is None:
                raise ValueError(f"tick {position} of the plane was left unreachable")

            read.append(token)
            position = self.origins[position]

        return tuple(reversed(read))
