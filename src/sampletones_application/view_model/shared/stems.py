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
    describes a recorded assignment. ``offered_channels`` names the boxes the row draws and
    ``channels`` the ones ticked among them.
    """

    key: str
    path: Path
    channels: FrozenSet[ChannelName]
    offered_channels: FrozenSet[ChannelName]
    available: bool
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
    def offers_channels(self) -> bool:
        """The row draws at least one box, so there is a channel to give the recording."""
        return bool(self.offered_channels)

    @property
    def in_play(self) -> bool:
        """The recording is there to be read and holds a channel, so what it carries is heard."""
        return self.available and self.takes_part

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
    """What a stems list renders: the rows, the columns they line up in, and how they answer.

    ``muted_channels`` names the columns a choice made elsewhere has switched off, which the
    boxes report while staying as clickable as any other. ``collapse_levels`` draws every row
    in one table, leaving the levels to the reader's memory rather than to a caption.
    """

    rows: Tuple[StemRowViewModel, ...]
    channels_in_play: Tuple[ChannelName, ...]
    muted_channels: FrozenSet[ChannelName]
    live: bool
    collapse_levels: bool

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
