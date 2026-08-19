from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import floor

from sampletones_player.clock.step import FixedPointStep
from sampletones_player.specification.clock import (
    FIXED_POINT_BITS,
    FIXED_POINT_SCALE,
    MAX_STEP_WHOLE,
    MICROSECONDS_PER_SECOND,
    PLAY_PERIOD_MICROSECONDS,
)


@dataclass(frozen=True)
class PlaySchedule:
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

    Initialisation leaves the stream on tick 0, and the play call at index ``play_call`` leaves it
    on tick ``ticks_at(play_call + 1)``.

    Attributes:
        ticks_per_play_call: The exact ticks one play call advances the stream by.
    """

    ticks_per_play_call: Fraction

    def __post_init__(self) -> None:
        if self.ticks_per_play_call <= 0:
            raise ValueError(f"ticks_per_play_call must be above 0, got {self.ticks_per_play_call}")

        if self.ticks_per_play_call > MAX_STEP_WHOLE:
            raise ValueError(f"ticks_per_play_call must be at most {MAX_STEP_WHOLE}, got {self.ticks_per_play_call}")

    @classmethod
    def from_parameters(cls, nes_frequency: int) -> PlaySchedule:
        """Derives the schedule a stream built at ``nes_frequency`` plays on.

        The play rate follows from the period the NSF header asks for, so the step the driver
        carries and the rate the file requests state the same clock.

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

        return cls(
            ticks_per_play_call=Fraction(
                nes_frequency * PLAY_PERIOD_MICROSECONDS,
                MICROSECONDS_PER_SECOND,
            ),
        )

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

    @property
    def fixed_point_step(self) -> FixedPointStep:
        """The exact step rounded to the nearest unit the driver's accumulator counts in."""
        whole, fraction = divmod(round(self.ticks_per_play_call * FIXED_POINT_SCALE), FIXED_POINT_SCALE)
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
