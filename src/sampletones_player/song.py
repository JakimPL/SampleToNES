from __future__ import annotations

from functools import cached_property
from typing import Optional, Sequence

from pydantic import BaseModel, ConfigDict, model_validator

from sampletones_player.clock.schedule import PlaySchedule
from sampletones_player.compression.compressed import CompressedPlanes
from sampletones_player.compression.dictionary.phrase import Phrase
from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.progress.report import SILENT_REPORTER, CodecReporter
from sampletones_player.compression.song import compress_song, decompress_song
from sampletones_player.registers.streams import ChannelStreams


class Song(BaseModel):
    """A song as the console holds it: compressed channel planes, a timer table and a clock.

    A file carries a song as eight token streams over one dictionary, and this is that song, so
    what the player holds and what the console reads are the same value. The register values each
    channel writes are read back out of the streams, the timer table turning a plane's pitch index
    into the divider the hardware takes.

    Attributes:
        planes: The dictionary and the eight token streams the channels play.
        pitches: The timer each pitch sounds at.
        schedule: The engine ticks each play call advances the streams by.
        loop_tick: The tick the song returns to once it ends, or ``None`` where it stops there.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    planes: CompressedPlanes
    pitches: PitchTable
    schedule: PlaySchedule
    loop_tick: Optional[int]

    @classmethod
    def from_streams(
        cls,
        streams: ChannelStreams,
        pitches: PitchTable,
        *,
        schedule: PlaySchedule,
        loop_tick: Optional[int],
        seeds: Sequence[Phrase],
        report: CodecReporter = SILENT_REPORTER,
    ) -> Song:
        """Compresses the register values a song plays into the song the console holds.

        Args:
            streams: The per-tick register values every channel plays.
            pitches: The timer each pitch sounds at.
            schedule: The engine ticks each play call advances the streams by.
            loop_tick: The tick the song returns to once it ends, or ``None`` where it stops
                there.
            seeds: The phrases the song's instruments offer the dictionary.
            report: Hears what the codec holds each time it looks up, and answers whether the
                compression goes on.

        Returns:
            Song: The song as the console holds it.

        Raises:
            OperationCancelled: If ``report`` withdraws the compression.
            ValueError: If ``loop_tick`` lies outside the song's ticks, or a channel sounds a
                timer the pitch table states no index for.
        """
        return cls(
            planes=compress_song(
                streams,
                pitches,
                seeds=seeds,
                loop_tick=loop_tick,
                report=report,
            ),
            pitches=pitches,
            schedule=schedule,
            loop_tick=loop_tick,
        )

    @model_validator(mode="after")
    def _validate_the_loop_lies_within_the_song(self) -> Song:
        if self.loop_tick is not None and not 0 <= self.loop_tick < self.ticks:
            raise ValueError(f"loop_tick must lie within the song's {self.ticks} ticks, got {self.loop_tick}")

        return self

    @property
    def ticks(self) -> int:
        """The ticks the song lasts."""
        return self.planes.ticks

    @cached_property
    def streams(self) -> ChannelStreams:
        """The per-tick register values every channel plays, read back out of the token streams.

        Every channel is carried to the song's full length, so one whose own instructions ran out
        first holds the silent values it stopped on through the ticks that remain.
        """
        return decompress_song(self.planes, self.pitches)

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
