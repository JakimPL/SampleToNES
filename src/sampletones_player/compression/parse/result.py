from dataclasses import dataclass
from typing import Tuple

from sampletones_player.compression.tokens.types import TokenUnion


@dataclass(frozen=True)
class Parse:
    """A plane read as tokens, alongside what each of its prefixes costs.

    Attributes:
        tokens: The tokens the plane is written as, in the order they are read.
        costs: The bytes each prefix of the plane takes, the whole plane's cost last.
    """

    tokens: Tuple[TokenUnion, ...]
    costs: Tuple[int, ...]

    @property
    def size(self) -> int:
        """The bytes the plane's token stream takes."""
        return self.costs[-1]
