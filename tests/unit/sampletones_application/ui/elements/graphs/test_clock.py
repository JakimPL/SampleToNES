from dataclasses import dataclass
from typing import Final, List

import pytest

from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.layout.graphs.clock import ClockLayout
from sampletones_application.ui.elements.graphs.clock import (
    clock_decimals,
    clock_step,
    clock_ticks,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

SAMPLE_RATE: Final[float] = 44100.0


@pytest.fixture(name="clock")
def clock_fixture(graphs_layout: GraphsLayout) -> ClockLayout:
    """The steps the shipped configuration offers, read where they are configured."""
    return graphs_layout.clock


class TestTheStepAStretchIsReadAt(BaseTestSuite):
    """The step is one a clock divides evenly into, and it grows with the stretch on screen."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        span_seconds: float
        expected_labels: List[str]

    test_cases = (
        TestCase(
            label="a whole song",
            span_seconds=175.0,
            expected_labels=["0:00", "0:30", "1:00", "1:30", "2:00", "2:30"],
        ),
        TestCase(
            label="a minute",
            span_seconds=60.0,
            expected_labels=["0:00", "0:10", "0:20", "0:30", "0:40", "0:50", "1:00"],
        ),
        TestCase(
            label="a couple of seconds",
            span_seconds=2.0,
            expected_labels=["0:00.0", "0:00.5", "0:01.0", "0:01.5", "0:02.0"],
        ),
        TestCase(
            label="a handful of frames",
            span_seconds=0.05,
            expected_labels=["0:00.00", "0:00.01", "0:00.02", "0:00.03", "0:00.04", "0:00.05"],
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_marks_it_reads_with(self, test_case: TestCase, clock: ClockLayout) -> None:
        ticks = clock_ticks(0.0, test_case.span_seconds, SAMPLE_RATE, clock)

        assert [label for label, _ in ticks] == test_case.expected_labels

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_step_is_one_the_configuration_offers(self, test_case: TestCase, clock: ClockLayout) -> None:
        assert clock_step(test_case.span_seconds, clock) in clock.steps_seconds


class TestHowFinelyASecondIsDivided:
    def test_a_step_of_seconds_reads_in_whole_seconds(self) -> None:
        assert clock_decimals(1.0) == 0
        assert clock_decimals(30.0) == 0

    def test_a_step_below_a_second_reads_in_tenths(self) -> None:
        assert clock_decimals(0.5) == 1

    def test_a_step_below_a_tenth_reads_in_hundredths(self) -> None:
        assert clock_decimals(0.05) == 2


class TestWhereTheMarksStand:
    def test_a_mark_stands_at_a_whole_multiple_of_the_step(self, clock: ClockLayout) -> None:
        ticks = clock_ticks(90.0, 98.0, SAMPLE_RATE, clock)

        assert [label for label, _ in ticks][:3] == ["1:30", "1:31", "1:32"]

    def test_a_mark_is_placed_where_its_moment_falls(self, clock: ClockLayout) -> None:
        ticks = clock_ticks(0.0, 8.0, SAMPLE_RATE, clock)

        assert ticks[1] == ("0:01", SAMPLE_RATE)

    def test_a_view_of_no_width_carries_no_marks(self, clock: ClockLayout) -> None:
        assert clock_ticks(5.0, 5.0, SAMPLE_RATE, clock) == []

    def test_a_rate_of_nothing_carries_no_marks(self, clock: ClockLayout) -> None:
        assert clock_ticks(0.0, 8.0, 0.0, clock) == []
