from __future__ import annotations

from fractions import Fraction
from functools import cached_property
from math import floor

from pydantic import BaseModel, ConfigDict, Field

from sampletones_player.clock.step import FixedPointStep
from sampletones_player.specification.clock import (
    FIXED_POINT_BITS,
    FIXED_POINT_SCALE,
    MAX_STEP_WHOLE,
    NTSC_FRAME_RATE,
    NTSC_NOMINAL_FRAME_RATE,
)


def play_rate_of(nes_frequency: int) -> Fraction:
    """The calls a second a stream built at ``nes_frequency`` is measured against.

    A rate that divides the console's nominal frame rate, or is a whole multiple of it, meets the
    frames evenly at that nominal rate. Every other rate is measured against the frame rate the
    console actually runs at.

    Args:
        nes_frequency: The engine tick rate the stream was built at, in Hz, at least 1.

    Returns:
        Fraction: `NTSC_NOMINAL_FRAME_RATE` for a rate that meets it evenly, `NTSC_FRAME_RATE` otherwise.
    """
    if NTSC_NOMINAL_FRAME_RATE % nes_frequency == 0 or nes_frequency % NTSC_NOMINAL_FRAME_RATE == 0:
        return Fraction(NTSC_NOMINAL_FRAME_RATE)

    return NTSC_FRAME_RATE


class PlaySchedule(BaseModel):
    """The engine ticks each play call advances a stream by, counted the way the console counts them.

    An NSF asks the console to call its play routine at one fixed rate, and a reconstruction is
    built at whatever rate its ``nes_frequency`` states. The two meet here: the schedule states how
    far the stream stands from its start after any number of calls, and the driver follows it by
    adding :attr:`fixed_point_step` to an accumulator and advancing by the whole ticks that fall
    out. One data set plays at every stream rate, and a stream slower than the play rate simply
    stands still on the calls between its ticks.

    Every answer about where the stream stands comes from that same rounded step, so the schedule
    states what the assembly does rather than what an unrounded clock would do. The exact rate
    stays as :attr:`ticks_per_play_call`, which is what :meth:`maximum_drift` measures against.

    This is the rule :class:`~sampletones_core.timing.clock.TickClock` applies one level down:
    spread the fractional part across consecutive units so the running total tracks the exact
    clock. There it is audio samples per engine tick; here it is engine ticks per play call.

    Initialization leaves the stream on tick 0, and the play call at index ``play_call`` leaves it
    on tick ``ticks_at(play_call + 1)``.

    Attributes:
        ticks_per_play_call: The exact ticks one play call advances the stream by.
        play_rate: The play calls a second the stream is measured against, which a file asks its
            player for.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    ticks_per_play_call: Fraction = Field(..., gt=0, le=MAX_STEP_WHOLE)
    play_rate: Fraction = Field(..., gt=0)

    @classmethod
    def from_parameters(cls, nes_frequency: int) -> PlaySchedule:
        """Derives the schedule a stream built at ``nes_frequency`` plays on.

        The console calls the play routine once a video frame, so a stream is read at its own
        rate measured against the frames, at the rate :func:`play_rate_of` picks. A stream at 60,
        30, 20 or 15 Hz, or at 120 Hz and the other multiples of 60, is measured against 60 calls
        a second: each tick holds the same calls, or each call advances the same ticks, and on a
        console it runs as much faster than built as `NTSC_FRAME_RATE` is faster than 60. Every
        other rate is measured against `NTSC_FRAME_RATE` and runs at its own speed there. The
        header asks for the rate the stream is measured against, so a player honoring the field
        runs every stream at the speed it was built at.

        Args:
            nes_frequency: The engine tick rate the reconstruction was built at, in Hz.

        Returns:
            PlaySchedule: The exact ticks one play call advances the stream by.

        Raises:
            ValueError: If ``nes_frequency`` is below 1, or asks for more ticks per call than the
                step's whole byte holds.
        """
        if nes_frequency < 1:
            raise ValueError(f"nes_frequency must be at least 1, got {nes_frequency}")

        play_rate = play_rate_of(nes_frequency)
        return cls(ticks_per_play_call=Fraction(nes_frequency) / play_rate, play_rate=play_rate)

    def ticks_at(self, play_calls: int) -> int:
        """The tick the stream stands on once ``play_calls`` calls have been made.

        Counts the way the driver counts: the rounded step added once per call, with the whole
        ticks read off the top of the running total. The console has only this arithmetic, so it
        is the schedule a song plays on, and :meth:`exact_ticks_at` is what it is measured against.

        Args:
            play_calls: How many play calls have been made, at least 0.

        Returns:
            int: The tick's index, within one tick of where the exact clock puts the stream.

        Raises:
            ValueError: If ``play_calls`` is negative.
        """
        if play_calls < 0:
            raise ValueError(f"play_calls must be at least 0, got {play_calls}")

        return (play_calls * self.fixed_point_step.value) >> FIXED_POINT_BITS

    def exact_ticks_at(self, play_calls: int) -> int:
        """The tick an unrounded clock puts the stream on once ``play_calls`` calls have been made.

        Args:
            play_calls: How many play calls have been made, at least 0.

        Returns:
            int: The tick's index, held in exact arithmetic.

        Raises:
            ValueError: If ``play_calls`` is negative.
        """
        if play_calls < 0:
            raise ValueError(f"play_calls must be at least 0, got {play_calls}")

        return floor(self.ticks_per_play_call * play_calls)

    def advance_at(self, play_call: int) -> int:
        """The ticks the stream advances by during the call at ``play_call``.

        Taking the difference of two cumulative counts is what makes a run of advances sum to the
        exact span it covers, however the fraction falls. This is the carry the driver reads out of
        its accumulator, and a carry of zero marks a call the stream holds its tick through.

        Args:
            play_call: The call's position in the run, counted from 0.

        Returns:
            int: The ticks that call advances by.

        Raises:
            ValueError: If ``play_call`` is negative.
        """
        return self.ticks_at(play_call + 1) - self.ticks_at(play_call)

    @cached_property
    def fixed_point_step(self) -> FixedPointStep:
        """The exact step rounded to the nearest unit the driver's accumulator counts in.

        Every answer the schedule gives counts in this step, so it is computed once and held.
        """
        whole, fraction = divmod(
            round(self.ticks_per_play_call * FIXED_POINT_SCALE),
            FIXED_POINT_SCALE,
        )
        return FixedPointStep(whole=whole, fraction=fraction)

    def maximum_drift(self, play_calls: int) -> int:
        """The furthest the driver's schedule stands from the exact one across a run of calls.

        Args:
            play_calls: How many calls the run covers, at least 0.

        Returns:
            int: The largest gap in ticks, measured at every call in the run.

        Raises:
            ValueError: If ``play_calls`` is negative.
        """
        if play_calls < 0:
            raise ValueError(f"play_calls must be at least 0, got {play_calls}")

        return max(
            abs(self.ticks_at(play_call) - self.exact_ticks_at(play_call)) for play_call in range(play_calls + 1)
        )
