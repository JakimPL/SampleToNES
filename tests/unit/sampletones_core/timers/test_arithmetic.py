from dataclasses import dataclass

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.general import MAX_TIMER, TIMER_CYCLE_DIVIDER
from sampletones_core.timers.arithmetic import (
    frequency_to_timer,
    get_timer_ticks,
    timer_to_frequency,
)
from sampletones_core.timers.utils import get_frequency_table, get_timer_table
from sampletones_shared.constants.music import A4_PITCH, LIMIT_MAX_PITCH, LIMIT_MIN_PITCH
from sampletones_shared.music import Tuning
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase


class TestFrequencyToTimer(BaseTestSuite):
    """The expected timers are the hardware's own values, which the APU reads back directly.

    A frequency beyond the 11-bit register's reach settles on the endpoint nearest it.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: int
        frequency: float

        @property
        def label(self) -> str:
            return f"frequency_{self.frequency:g}"

    test_cases = (
        TestCase(frequency=0.0, expected=0),
        TestCase(frequency=-1.0, expected=0),
        TestCase(frequency=440.0, expected=253),
        TestCase(frequency=0.001, expected=MAX_TIMER),
        TestCase(frequency=1e9, expected=0),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_timer_matches(self, test_case: TestCase) -> None:
        assert frequency_to_timer(test_case.frequency) == test_case.expected


class TestGetTimerTicks(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: int
        timer: int

        @property
        def label(self) -> str:
            return f"timer_{self.timer}"

    test_cases = (
        TestCase(timer=0, expected=0),
        TestCase(timer=-1, expected=0),
        TestCase(timer=1, expected=2 * TIMER_CYCLE_DIVIDER),
        TestCase(timer=100, expected=101 * TIMER_CYCLE_DIVIDER),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_cycle_count_matches(self, test_case: TestCase) -> None:
        assert get_timer_ticks(test_case.timer) == test_case.expected


class TestTimerRoundTrip:
    """Reading a timer back as a frequency and converting it again returns the same timer.

    This is what lets a timer table be derived from a frequency table without drifting: the
    frequency a table holds is already one the divider reaches exactly.
    """

    @pytest.mark.parametrize("timer", [0, 1, 8, 253, 1000, MAX_TIMER])
    def test_frequency_maps_back_to_its_timer(self, timer: int) -> None:
        assert frequency_to_timer(timer_to_frequency(timer)) == timer


class TestGetTimerTable:
    def test_covers_every_pitch_the_project_sounds(self) -> None:
        timers = get_timer_table(Tuning())
        assert set(timers) == set(range(LIMIT_MIN_PITCH, LIMIT_MAX_PITCH + 1))

    def test_every_timer_sounds_its_pitch_frequency(self) -> None:
        config = Config()
        frequencies = get_frequency_table(config)
        timers = get_timer_table(config.tuning)

        for pitch, frequency in frequencies.items():
            assert timer_to_frequency(timers[pitch]) == frequency

    def test_a_retuned_table_follows_concert_pitch(self) -> None:
        standard = get_timer_table(Tuning())
        retuned = get_timer_table(Tuning(a4_frequency=432.0))
        assert retuned[A4_PITCH] > standard[A4_PITCH]
