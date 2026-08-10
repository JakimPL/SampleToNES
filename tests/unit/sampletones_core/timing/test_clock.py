from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Final, Tuple

import pytest

from sampletones_core.constants.audio import SAMPLE_RATES
from sampletones_core.timing.clock import TickClock
from sampletones_shared.constants.nes import MAX_NES_FREQUENCY, MIN_NES_FREQUENCY
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase

LONG_RUN_TICKS: Final[int] = 36000
NES_FREQUENCIES: Final[Tuple[int, ...]] = (15, 24, 25, 30, 50, 60, 100, 120, 199, 300)


class TestTickClock(BaseTestSuite):
    """One case table, read both for the frame lengths it produces and for the rules they obey."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: Tuple[int, ...]
        sample_rate: int
        nes_frequency: int

        @property
        def label(self) -> str:
            return f"{self.sample_rate}hz_{self.nes_frequency}tick"

        @property
        def clock(self) -> TickClock:
            return TickClock.from_parameters(
                sample_rate=self.sample_rate,
                nes_frequency=self.nes_frequency,
            )

    test_cases = (
        TestCase(sample_rate=44100, nes_frequency=60, expected=(735,) * 8),
        TestCase(sample_rate=48000, nes_frequency=60, expected=(800,) * 8),
        TestCase(sample_rate=96000, nes_frequency=60, expected=(1600,) * 8),
        TestCase(sample_rate=44100, nes_frequency=30, expected=(1470,) * 8),
        TestCase(
            sample_rate=22050,
            nes_frequency=60,
            expected=(367, 368, 367, 368, 367, 368, 367, 368),
        ),
        TestCase(
            sample_rate=8000,
            nes_frequency=60,
            expected=(133, 133, 134, 133, 133, 134, 133, 133),
        ),
        TestCase(
            sample_rate=16000,
            nes_frequency=60,
            expected=(266, 267, 267, 266, 267, 267, 266, 267),
        ),
        TestCase(
            sample_rate=44100,
            nes_frequency=120,
            expected=(367, 368, 367, 368, 367, 368, 367, 368),
        ),
        TestCase(
            sample_rate=8000,
            nes_frequency=300,
            expected=(26, 27, 27, 26, 27, 27, 26, 27),
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_frame_lengths_match(self, test_case: TestCase) -> None:
        clock = test_case.clock
        lengths = tuple(clock.frame_length(tick) for tick in range(len(test_case.expected)))
        assert lengths == test_case.expected

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_frame_lengths_sum_to_the_cumulative_count(self, test_case: TestCase) -> None:
        clock = test_case.clock
        assert sum(clock.frame_length(tick) for tick in range(len(test_case.expected))) == clock.samples_at(
            len(test_case.expected)
        )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_only_the_floor_and_the_ceiling_appear(self, test_case: TestCase) -> None:
        """Consecutive ticks differ by at most one sample, so no tick is audibly off on its own."""
        clock = test_case.clock
        lengths = {clock.frame_length(tick) for tick in range(LONG_RUN_TICKS)}
        assert max(lengths) - min(lengths) <= 1

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_is_exact_reports_a_uniform_run(self, test_case: TestCase) -> None:
        clock = test_case.clock
        lengths = {clock.frame_length(tick) for tick in range(LONG_RUN_TICKS)}
        assert clock.is_exact == (len(lengths) == 1)


class TestTheClockHoldsTheTempo(BaseTestSuite):
    """The property the whole clock exists for: a run of ticks lands on its exact duration."""

    @pytest.mark.parametrize("nes_frequency", NES_FREQUENCIES)
    @pytest.mark.parametrize("sample_rate", SAMPLE_RATES)
    def test_a_long_run_lands_on_the_exact_sample_count(
        self,
        sample_rate: int,
        nes_frequency: int,
    ) -> None:
        clock = TickClock.from_parameters(
            sample_rate=sample_rate,
            nes_frequency=nes_frequency,
        )
        rendered = sum(clock.frame_length(tick) for tick in range(LONG_RUN_TICKS))
        exact = Fraction(sample_rate, nes_frequency) * LONG_RUN_TICKS
        assert rendered == int(exact) if exact.denominator == 1 else abs(rendered - exact) < 1

    @pytest.mark.parametrize("nes_frequency", NES_FREQUENCIES)
    @pytest.mark.parametrize("sample_rate", SAMPLE_RATES)
    def test_the_cumulative_count_never_drifts_past_one_sample(
        self,
        sample_rate: int,
        nes_frequency: int,
    ) -> None:
        clock = TickClock.from_parameters(
            sample_rate=sample_rate,
            nes_frequency=nes_frequency,
        )
        rate = Fraction(sample_rate, nes_frequency)
        assert all(abs(clock.samples_at(ticks) - rate * ticks) < 1 for ticks in range(0, LONG_RUN_TICKS, 97))

    @pytest.mark.parametrize("sample_rate", SAMPLE_RATES)
    def test_a_whole_division_gives_every_tick_the_rounded_length(self, sample_rate: int) -> None:
        """Where the division is whole the clock agrees with the length a timer is built with."""
        for nes_frequency in NES_FREQUENCIES:
            if sample_rate % nes_frequency:
                continue

            clock = TickClock.from_parameters(
                sample_rate=sample_rate,
                nes_frequency=nes_frequency,
            )
            expected = round(sample_rate / nes_frequency)
            assert clock.is_exact
            assert all(clock.frame_length(tick) == expected for tick in range(64))


class TestTickClockBounds(BaseTestSuite):
    def test_the_first_tick_starts_at_zero(self) -> None:
        clock = TickClock.from_parameters(sample_rate=44100, nes_frequency=60)
        assert clock.samples_at(0) == 0

    def test_every_tick_spans_at_least_one_sample(self) -> None:
        clock = TickClock.from_parameters(
            sample_rate=min(SAMPLE_RATES),
            nes_frequency=MAX_NES_FREQUENCY,
        )
        assert all(clock.frame_length(tick) >= 1 for tick in range(1024))

    @pytest.mark.parametrize("nes_frequency", (MIN_NES_FREQUENCY, MAX_NES_FREQUENCY))
    def test_the_engine_range_is_covered_at_every_rate(self, nes_frequency: int) -> None:
        for sample_rate in SAMPLE_RATES:
            clock = TickClock.from_parameters(
                sample_rate=sample_rate,
                nes_frequency=nes_frequency,
            )
            assert clock.samples_per_tick == Fraction(sample_rate, nes_frequency)

    def test_a_tick_shorter_than_a_sample_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="samples_per_tick must be at least 1"):
            TickClock.from_parameters(sample_rate=100, nes_frequency=300)

    @pytest.mark.parametrize("sample_rate", (0, -1))
    def test_a_rate_below_one_is_rejected(self, sample_rate: int) -> None:
        with pytest.raises(ValueError, match="sample_rate must be at least 1"):
            TickClock.from_parameters(sample_rate=sample_rate, nes_frequency=60)

    @pytest.mark.parametrize("nes_frequency", (0, -1))
    def test_a_tick_rate_below_one_is_rejected(self, nes_frequency: int) -> None:
        with pytest.raises(ValueError, match="nes_frequency must be at least 1"):
            TickClock.from_parameters(sample_rate=44100, nes_frequency=nes_frequency)

    def test_a_negative_tick_count_is_rejected(self) -> None:
        clock = TickClock.from_parameters(sample_rate=44100, nes_frequency=60)
        with pytest.raises(ValueError, match="ticks must be at least 0"):
            clock.samples_at(-1)
