from dataclasses import dataclass

from sampletones_player.compression.tokens.sizes import hold_size


@dataclass(frozen=True)
class HoldToken:
    """The plane keeps the value it reached, for ``ticks`` ticks."""

    ticks: int

    @property
    def size(self) -> int:
        """The bytes the token takes."""
        return hold_size()
