from dataclasses import dataclass
from typing import Tuple

from sampletones_player.compression.matches.index import PlaneIndex
from sampletones_player.compression.matches.matcher import PhraseMatcher
from sampletones_player.compression.parse.boundaries import Boundaries
from sampletones_tools.codec.study.sandbox.costs import Costs


@dataclass(frozen=True)
class PlaneContext:
    """One plane as a grammar reads it: its values, the phrases it may play, and the terms.

    Attributes:
        index: The plane, its steps and its runs.
        matcher: Which phrases the plane plays at a symbol, and for how long.
        boundaries: The symbols a token starts on, read either way from every symbol.
        transposition: Whether a phrase may play at a shift.
        defaults: The default count of each phrase, by id, zero where the phrase has none.
        seeded: The symbol the plane stands at before its first token.
        costs: The bytes each token takes.
    """

    index: PlaneIndex
    matcher: PhraseMatcher
    boundaries: Boundaries
    transposition: bool
    defaults: Tuple[int, ...]
    seeded: int
    costs: Costs

    def value_before(self, position: int) -> int:
        """The symbol the plane holds as ``position`` is reached, which a hold there keeps.

        The driver seeds every plane before the first token, so the stream's first symbol is
        reached holding the seeded symbol like any other.

        Args:
            position: The symbol.

        Returns:
            int: The symbol held.
        """
        return self.index.plane[position - 1] if position > 0 else self.seeded
