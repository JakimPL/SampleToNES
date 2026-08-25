from dataclasses import dataclass

from sampletones_player.compression.tokens.sizes import literal_size


@dataclass(frozen=True)
class LiteralToken:
    """The plane takes the values verbatim, one per tick."""

    values: bytes

    @property
    def ticks(self) -> int:
        """The ticks the token covers."""
        return len(self.values)

    @property
    def size(self) -> int:
        """The bytes the token takes."""
        return literal_size(len(self.values))
