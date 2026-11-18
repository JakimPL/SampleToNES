from __future__ import annotations

from typing import Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from sampletones_player.song import Song
from sampletones_player.specification.clock import FIXED_POINT_BITS, FIXED_POINT_SCALE
from sampletones_player.specification.program import (
    DIGIT_BASE,
    LONGEST_SHOWN_SECONDS,
    NO_LOOP_FRAMES,
    PROGRESS_PIXELS,
    SECOND_STEP,
    SECONDS_PER_MINUTE,
)

ClockDigits = Tuple[int, int, int, int]


def frames_until(tick: int, step: int) -> int:
    """The play calls after which a stream advancing by ``step`` stands on ``tick`` or beyond it."""
    return -(-(tick << FIXED_POINT_BITS) // step)


def clock_digits(seconds: int) -> ClockDigits:
    """The four digits the screen shows a time as, minutes then seconds, held at the longest it shows."""
    minutes, rest = divmod(min(seconds, LONGEST_SHOWN_SECONDS), SECONDS_PER_MINUTE)
    return (minutes // DIGIT_BASE, minutes % DIGIT_BASE, rest // DIGIT_BASE, rest % DIGIT_BASE)


class ProgramClock(BaseModel):
    """The frames a cartridge counts a song's time and progress in.

    The cartridge advances its clock and its progress bar once a frame by fixed steps, and knows
    when the song ends or comes round by counting frames down. Every figure it starts from is
    worked out here with the same arithmetic, so the screen shows the time the frames add up to.

    Attributes:
        total_frames: The frames the song takes to run past its end the first time.
        loop_frame: The frames the song takes to reach its loop tick the first time, or ``None``
            for a song that ends.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    total_frames: int = Field(..., ge=1)
    loop_frame: Optional[int] = Field(..., ge=0)

    @classmethod
    def of(cls, song: Song) -> ProgramClock:
        """The frames a song's schedule puts its end and its loop tick at.

        Initialization leaves the song on tick 0, and the song stands on a tick once the
        schedule's count after that many calls reaches it.
        """
        step = song.schedule.fixed_point_step.value
        return cls(
            total_frames=frames_until(song.ticks, step),
            loop_frame=None if song.loop_tick is None else frames_until(song.loop_tick, step),
        )

    @property
    def progress_step(self) -> int:
        """The pixels the progress bar grows by a frame, in 1/65536ths, filling it as the song ends."""
        return PROGRESS_PIXELS * FIXED_POINT_SCALE // self.total_frames

    @property
    def loop_frames(self) -> int:
        """The frames from the loop tick to the end, which the cartridge counts down on every repeat."""
        if self.loop_frame is None:
            return NO_LOOP_FRAMES

        return max(self.total_frames - self.loop_frame, NO_LOOP_FRAMES + 1)

    @property
    def total_time(self) -> ClockDigits:
        """The time the song's first run takes."""
        return clock_digits(self.seconds_at(self.total_frames))

    @property
    def loop_time(self) -> ClockDigits:
        """The time the clock goes back to when the song comes round."""
        return clock_digits(self.seconds_at(self.loop_frame or 0))

    @property
    def loop_second(self) -> int:
        """The part of a second the clock holds when the song comes round, in 1/65536ths."""
        return ((self.loop_frame or 0) * SECOND_STEP) % FIXED_POINT_SCALE

    @property
    def loop_progress(self) -> int:
        """Where the progress bar goes back to when the song comes round, in 1/65536ths of a pixel."""
        return (self.loop_frame or 0) * self.progress_step

    @staticmethod
    def seconds_at(frames: int) -> int:
        """The whole seconds the clock shows after ``frames`` frames."""
        return (frames * SECOND_STEP) >> FIXED_POINT_BITS
