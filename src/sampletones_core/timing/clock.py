from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import floor


@dataclass(frozen=True)
class TickClock:
    """The audio samples each engine tick spans, held exact so a tick lasts what the engine holds it for.

    A tick is the interrupt the engine consumes one instruction on, and it lasts
    ``1 / nes_frequency`` seconds whatever rate the audio is rendered at. Where that duration
    falls between two samples, giving every tick the same rounded length shifts the tempo by
    the rounding, and the shift accumulates over a song. Spreading the fractional part across
    consecutive ticks instead holds the running total on the exact clock, so the tempo a
    :class:`~sampletones_core.timing.groove.Groove` states is the tempo the audio plays at, at
    any sample rate.

    This is the rule a groove applies, one level down: a groove spreads a fractional ticks-per-row
    across a pattern's rows, and a tick clock spreads a fractional samples-per-tick across the
    ticks themselves. Both answer with whole numbers that sum to the exact total.

    Attributes:
        samples_per_tick: The exact samples one tick spans.
    """

    samples_per_tick: Fraction

    def __post_init__(self) -> None:
        if self.samples_per_tick < 1:
            raise ValueError(f"samples_per_tick must be at least 1, got {self.samples_per_tick}")

    @classmethod
    def from_parameters(
        cls,
        *,
        sample_rate: int,
        nes_frequency: int,
    ) -> TickClock:
        """Derives the clock a render at ``sample_rate`` runs the engine's ticks on.

        Args:
            sample_rate: The audio sample rate in Hz.
            nes_frequency: The engine tick rate in Hz.

        Returns:
            TickClock: The exact samples one tick spans at those rates.

        Raises:
            ValueError: If either rate is below 1, or a tick spans less than one sample.
        """
        if sample_rate < 1:
            raise ValueError(f"sample_rate must be at least 1, got {sample_rate}")

        if nes_frequency < 1:
            raise ValueError(f"nes_frequency must be at least 1, got {nes_frequency}")

        return cls(samples_per_tick=Fraction(sample_rate, nes_frequency))

    @property
    def is_exact(self) -> bool:
        """Whether every tick spans the same whole number of samples."""
        return self.samples_per_tick.denominator == 1

    def samples_at(self, ticks: int) -> int:
        """The samples the first ``ticks`` ticks span together.

        Args:
            ticks: How many ticks have elapsed, at least 0.

        Returns:
            int: The cumulative sample count, within one sample of the exact duration.

        Raises:
            ValueError: If ``ticks`` is negative.
        """
        if ticks < 0:
            raise ValueError(f"ticks must be at least 0, got {ticks}")

        return floor(self.samples_per_tick * ticks)

    def frame_length(self, tick_index: int) -> int:
        """The samples the tick at ``tick_index`` spans.

        Taking the difference of two cumulative counts is what makes a run of frame lengths sum
        to the exact span of the ticks it covers, however the fraction falls.

        Args:
            tick_index: The tick's position in the run, counted from 0.

        Returns:
            int: The tick's length in samples.

        Raises:
            ValueError: If ``tick_index`` is negative.
        """
        return self.samples_at(tick_index + 1) - self.samples_at(tick_index)
