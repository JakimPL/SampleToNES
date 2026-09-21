from dataclasses import dataclass
from typing import Tuple

import pytest
from pydantic import ValidationError

from sampletones_player.compression.budget import (
    DEFAULT_SEARCH_BUDGET,
    SearchBudget,
    shares,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


class TestSharesMeetSmallDemandsAndSplitTheRest(BaseTestSuite):
    """A claimant asking for little is served whole; the larger ones split what remains evenly."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        demands: Tuple[int, ...]
        total: int
        expected: Tuple[int, ...]

    test_cases = (
        TestCase(
            label="every_demand_fits",
            demands=(5, 5, 5),
            total=30,
            expected=(5, 5, 5),
        ),
        TestCase(
            label="a_small_demand_leaves_its_surplus",
            demands=(100, 1, 100),
            total=41,
            expected=(20, 1, 20),
        ),
        TestCase(
            label="a_zero_demand_takes_nothing",
            demands=(0, 7),
            total=3,
            expected=(0, 3),
        ),
        TestCase(
            label="equal_demands_split_evenly",
            demands=(9, 9),
            total=8,
            expected=(4, 4),
        ),
        TestCase(
            label="a_total_short_of_one_each",
            demands=(9, 9, 9),
            total=2,
            expected=(0, 1, 1),
        ),
        TestCase(label="no_claimants", demands=(), total=10, expected=()),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_shares(self, test_case: TestCase) -> None:
        assert shares(test_case.demands, test_case.total) == test_case.expected

    def test_the_total_is_never_exceeded(self) -> None:
        demands = (30, 70, 10, 90)
        for total in range(0, 220, 7):
            assert sum(shares(demands, total)) <= total


class TestTheBudgetBoundsEveryStep:
    """Each figure is at least what one round can act on, and the default states them all."""

    def test_the_default_gathers_ranks_and_confirms(self) -> None:
        assert DEFAULT_SEARCH_BUDGET.candidate_entries >= 1
        assert DEFAULT_SEARCH_BUDGET.rounds >= 1
        assert DEFAULT_SEARCH_BUDGET.confirmed_candidates >= 1

    def test_a_round_gathers_at_least_one_entry(self) -> None:
        with pytest.raises(ValidationError):
            SearchBudget(candidate_entries=0, rounds=1, confirmed_candidates=1)

    def test_a_round_confirms_at_least_one_candidate(self) -> None:
        with pytest.raises(ValidationError):
            SearchBudget(candidate_entries=1, rounds=1, confirmed_candidates=0)

    def test_no_rounds_is_a_budget(self) -> None:
        assert SearchBudget(candidate_entries=1, rounds=0, confirmed_candidates=1).rounds == 0
