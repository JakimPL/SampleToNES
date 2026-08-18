from dataclasses import dataclass
from typing import Optional

from sampletones_player.clock.schedule import PlaySchedule
from sampletones_player.registers.streams import ChannelStreams


@dataclass(frozen=True)
class Song:
    """A reconstruction as the player holds it: the four streams, the clock, and where it repeats.

    Attributes:
        streams: The per-tick register values every channel plays.
        schedule: The engine ticks each play call advances the streams by.
        loop_tick: The tick the song returns to once it ends, or ``None`` where it stops there.
    """

    streams: ChannelStreams
    schedule: PlaySchedule
    loop_tick: Optional[int]

    def __post_init__(self) -> None:
        if self.loop_tick is not None and not 0 <= self.loop_tick < self.ticks:
            raise ValueError(f"loop_tick must lie within the song's {self.ticks} ticks, got {self.loop_tick}")

    @property
    def ticks(self) -> int:
        """The ticks the song lasts."""
        return self.streams.ticks

    def tick_at(self, play_call: int) -> Optional[int]:
        """The tick the call at ``play_call`` leaves the streams on.

        A song that runs past its end either returns to its loop tick and keeps going, or stops
        and leaves the channels holding the silent values its final tick wrote.

        Args:
            play_call: The call's position in the run, counted from 0.

        Returns:
            Optional[int]: The tick to play, or ``None`` once a song without a loop has ended.
        """
        tick = self.schedule.ticks_at(play_call + 1)
        if tick < self.ticks:
            return tick

        if self.loop_tick is None:
            return None

        return self.loop_tick + (tick - self.ticks) % (self.ticks - self.loop_tick)
