from dataclasses import dataclass
from typing import Union

from sampletones_player.specification.compression import MAX_HOLD_TICKS


@dataclass(frozen=True)
class Hold:
    """The plane keeps the value it reached, for ``ticks`` ticks."""

    ticks: int


@dataclass(frozen=True)
class WideHold:
    """The plane keeps the value it reached for ``blocks`` blocks of a plain hold's longest reach (H1)."""

    blocks: int

    @property
    def ticks(self) -> int:
        """The ticks the token covers."""
        return self.blocks * MAX_HOLD_TICKS


@dataclass(frozen=True)
class SetHold:
    """The plane takes ``value`` and keeps it for ``ticks`` ticks (H3)."""

    value: int
    ticks: int


@dataclass(frozen=True)
class Literal:
    """The plane takes the values verbatim, one per tick."""

    values: bytes

    @property
    def ticks(self) -> int:
        """The ticks the token covers."""
        return len(self.values)


@dataclass(frozen=True)
class Play:
    """The plane plays a phrase from the table, shifted by ``transpose``, for ``ticks`` ticks.

    A default play covers the phrase's own default count and carries no count of its own (H4).
    """

    phrase_id: int
    ticks: int
    transpose: int
    default: bool


StudyToken = Union[Hold, WideHold, SetHold, Literal, Play]
