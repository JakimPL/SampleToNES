from pathlib import Path
from typing import FrozenSet, Tuple

from pydantic import BaseModel

from sampletones_core.constants.enums import ChannelName


class StemRowViewModel(BaseModel, frozen=True):
    """One recording in a stems list, as the list renders it.

    A row states where it stands — the level it picks on, the place it takes among the
    recordings sharing that level, and how many of each the list holds — so the moves a list
    offers grey themselves out from the row alone. ``key`` is the identity the list reports a
    gesture under: the recording's path where the list gathers files, the stem id where it
    describes a recorded assignment.
    """

    key: str
    path: Path
    channels: FrozenSet[ChannelName]
    level: int
    position: int
    level_size: int
    level_count: int

    @property
    def name(self) -> str:
        """The recording's own name, which is what the row reads as."""
        return self.path.stem

    @property
    def takes_part(self) -> bool:
        """The recording holds a channel, so the list counts it in."""
        return bool(self.channels)

    @property
    def is_first_on_level(self) -> bool:
        return self.position == 0

    @property
    def is_last_on_level(self) -> bool:
        return self.position == self.level_size - 1

    @property
    def has_level_above(self) -> bool:
        return self.level > 0

    @property
    def has_level_below(self) -> bool:
        return self.level < self.level_count - 1

    @property
    def alone_on_level(self) -> bool:
        return self.level_size == 1


class StemsListViewModel(BaseModel, frozen=True):
    """What a stems list renders: the rows, the columns they line up in, and whether they answer."""

    rows: Tuple[StemRowViewModel, ...]
    channels_in_play: Tuple[ChannelName, ...]
    live: bool

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def level_count(self) -> int:
        """How many levels the listed recordings are spread over."""
        return max((row.level + 1 for row in self.rows), default=0)

    @property
    def playing_count(self) -> int:
        """How many of the listed recordings hold a channel."""
        return sum(1 for row in self.rows if row.takes_part)
