from dataclasses import dataclass
from typing import Final, List, Optional, Tuple

import pytest

from sampletones_core.reconstructions.reconstructor.refinement.smoothing import smoothed
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

WINDOW: Final[int] = 4
CHANGE_WEIGHT: Final[float] = 2.0


def _smoothed(proposals: List[Optional[int]]) -> List[int]:
    return smoothed(proposals, window=WINDOW, change_weight=CHANGE_WEIGHT)


class TestWhatTheWalkSettlesOn(BaseTestSuite):
    """The walk follows the readings while paying a toll on every change it makes."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        proposals: Tuple[Optional[int], ...]
        expected: Tuple[int, ...]

    test_cases: Tuple["TestWhatTheWalkSettlesOn.TestCase", ...] = (
        TestCase(label="nothing read", proposals=(), expected=()),
        TestCase(label="one reading", proposals=(5,), expected=(5,)),
        TestCase(
            label="a steady reading is kept",
            proposals=(3, 3, 3, 3),
            expected=(3, 3, 3, 3),
        ),
        TestCase(
            label="a single stray reading is absorbed",
            proposals=(3, 3, 6, 3, 3),
            expected=(3, 3, 3, 3, 3),
        ),
        TestCase(
            label="a stray reading worth two tolls is followed",
            proposals=(3, 3, 12, 3, 3),
            expected=(3, 3, 12, 3, 3),
        ),
        TestCase(
            label="a reading that holds is followed",
            proposals=(3, 3, 3, -8, -8, -8, -8),
            expected=(3, 3, 3, -8, -8, -8, -8),
        ),
        TestCase(
            label="frames that read nothing rest at no bend",
            proposals=(None, None, None),
            expected=(0, 0, 0),
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_walk_settles_where_the_readings_point(
        self,
        test_case: "TestWhatTheWalkSettlesOn.TestCase",
    ) -> None:
        assert tuple(_smoothed(list(test_case.proposals))) == test_case.expected


class TestTheTollOnChanging:
    def test_a_walk_paying_nothing_to_change_follows_every_reading(self) -> None:
        proposals: List[Optional[int]] = [3, 9, 3, 9]

        assert smoothed(proposals, window=WINDOW, change_weight=0.0) == [3, 9, 3, 9]

    def test_a_walk_that_cannot_afford_a_change_holds_one_bend(self) -> None:
        proposals: List[Optional[int]] = [3, 9, 3, 9]

        assert len(set(smoothed(proposals, window=WINDOW, change_weight=1000.0))) == 1

    def test_an_excursion_is_absorbed_while_it_stays_within_two_tolls(self) -> None:
        """Leaving a bend and returning costs two changes, which is what a blip has to beat."""
        toll = int(2 * CHANGE_WEIGHT)
        held: List[Optional[int]] = [3, 3, 3 + toll, 3, 3]
        beyond: List[Optional[int]] = [3, 3, 3 + toll * 2, 3, 3]

        assert _smoothed(held) == [3, 3, 3, 3, 3]
        assert _smoothed(beyond)[2] != 3

    def test_a_frame_that_read_nothing_costs_the_walk_nothing(self) -> None:
        """A gap in the readings neither pulls the bend nor pays for holding it."""
        proposals: List[Optional[int]] = [4, 4, None, None, 4, 4]

        assert _smoothed(proposals) == [4, 4, 4, 4, 4, 4]

    def test_every_frame_answers(self) -> None:
        proposals: List[Optional[int]] = [1, None, 2, None, 3]

        assert len(_smoothed(proposals)) == len(proposals)


class TestTheStatesTheWalkConsiders:
    def test_the_walk_settles_only_on_bends_its_neighborhood_read(self) -> None:
        """The states are the readings, so a divider range spanning tens of steps stays small."""
        proposals: List[Optional[int]] = [10, 20, 30]

        assert set(_smoothed(proposals)) <= {0, 10, 20, 30}

    def test_a_reading_beyond_the_window_is_out_of_reach(self) -> None:
        """A frame settles on what stands near it, so a distant reading pulls it no further."""
        proposals: List[Optional[int]] = [7] + [None] * (WINDOW * 3) + [7]

        settled = smoothed(proposals, window=1, change_weight=CHANGE_WEIGHT)

        assert settled[len(proposals) // 2] == 0
