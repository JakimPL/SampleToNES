from dataclasses import dataclass
from typing import Dict, Final, Tuple

from sampletones_core.constants.enums import ChannelName

ABSENT_REGISTER: Final[int] = 0


@dataclass(frozen=True)
class ChannelSound:
    """What one channel sounds on one engine tick, in the values its registers hold.

    Both players are read into this one shape, so a tick of the application and a tick of a tracker
    compare field by field. A register the channel lacks reads as ``ABSENT_REGISTER`` on both sides.

    Attributes:
        audible: Whether the channel sounds at all.
        period: The period register: the 11-bit timer on the pulse and triangle channels, and the
            4-bit period index on the noise channel.
        volume: The level on the pulse and noise channels.
        timbre: The duty cycle on the pulse channels, and the short mode on the noise channel.
    """

    audible: bool
    period: int
    volume: int
    timbre: int


@dataclass(frozen=True)
class TickPosition:
    """Where in the song one engine tick falls.

    Attributes:
        frame: The order frame being played.
        row: The row of that frame's patterns.
    """

    frame: int
    row: int


@dataclass(frozen=True)
class SongTrace:
    """What every channel sounds on every engine tick of one pass through a song.

    Attributes:
        positions: Where each tick falls, one per tick.
        channels: Each channel's sound, one per tick.
    """

    positions: Tuple[TickPosition, ...]
    channels: Dict[ChannelName, Tuple[ChannelSound, ...]]

    @property
    def ticks(self) -> int:
        """The engine ticks the pass lasts."""
        return len(self.positions)
