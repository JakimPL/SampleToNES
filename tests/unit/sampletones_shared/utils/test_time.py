from dataclasses import dataclass

import pytest

from sampletones_shared.utils.time import (
    format_clock,
    format_span,
    seconds_from_samples,
    seconds_from_ticks,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


class TestHowLongSomethingLasts(BaseTestSuite):
    """A span names its units and reads in the largest ones it fills."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        seconds: float
        expected: str

    test_cases = (
        TestCase(label="nothing at all", seconds=0.0, expected="0s"),
        TestCase(label="a part of a second", seconds=0.4, expected="0s"),
        TestCase(label="seconds alone", seconds=13.0, expected="13s"),
        TestCase(label="the last second before a minute", seconds=59.0, expected="59s"),
        TestCase(label="a whole minute", seconds=60.0, expected="1m 00s"),
        TestCase(label="minutes and seconds", seconds=133.0, expected="2m 13s"),
        TestCase(label="a whole hour", seconds=3600.0, expected="1h 00m 00s"),
        TestCase(label="hours, minutes and seconds", seconds=3733.0, expected="1h 02m 13s"),
        TestCase(label="a span read backwards", seconds=-5.0, expected="0s"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_span_it_reads_as(self, test_case: TestCase) -> None:
        assert format_span(test_case.seconds) == test_case.expected


class TestHowFarIntoSomethingAMomentStands(BaseTestSuite):
    """A position reads as a clock, at the precision the reading asks for."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        seconds: float
        decimals: int
        expected: str

    test_cases = (
        TestCase(label="the start", seconds=0.0, decimals=0, expected="0:00"),
        TestCase(label="a few seconds in", seconds=3.0, decimals=0, expected="0:03"),
        TestCase(label="minutes and seconds", seconds=133.0, decimals=0, expected="2:13"),
        TestCase(label="past an hour", seconds=3733.0, decimals=0, expected="1:02:13"),
        TestCase(label="tenths of a second", seconds=90.25, decimals=1, expected="1:30.2"),
        TestCase(label="hundredths of a second", seconds=90.25, decimals=2, expected="1:30.25"),
        TestCase(label="the start at hundredths", seconds=0.0, decimals=2, expected="0:00.00"),
        TestCase(label="a second rounding into its minute", seconds=59.96, decimals=1, expected="1:00.0"),
        TestCase(label="a minute rounding into its hour", seconds=3599.5, decimals=0, expected="1:00:00"),
        TestCase(label="a moment read before the start", seconds=-5.0, decimals=0, expected="0:00"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_clock_it_reads_as(self, test_case: TestCase) -> None:
        assert format_clock(test_case.seconds, test_case.decimals) == test_case.expected


class TestWhatALengthAmountsTo:
    def test_samples_last_the_seconds_their_rate_gives_them(self) -> None:
        assert seconds_from_samples(88200, 44100) == pytest.approx(2.0)

    def test_ticks_last_the_seconds_their_rate_gives_them(self) -> None:
        assert seconds_from_ticks(90, 60) == pytest.approx(1.5)

    def test_a_rate_of_nothing_measures_nothing(self) -> None:
        assert seconds_from_samples(88200, 0) == 0.0
        assert seconds_from_ticks(90, 0) == 0.0
