from dataclasses import dataclass
from typing import Tuple

import pytest

from sampletones_application.logic.main.sources.agreement import Agreement
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


class TestTheReadingAGroupGives(BaseTestSuite):
    """A row standing for several recordings reads as what they agree on."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Agreement
        holdings: Tuple[bool, ...]

    test_cases = (
        TestCase(label="standing_for_nothing", holdings=(), expected=Agreement.NONE),
        TestCase(label="one_holding_it", holdings=(True,), expected=Agreement.ALL),
        TestCase(label="one_leaving_it", holdings=(False,), expected=Agreement.NONE),
        TestCase(label="every_one_holding_it", holdings=(True, True, True), expected=Agreement.ALL),
        TestCase(label="none_holding_it", holdings=(False, False), expected=Agreement.NONE),
        TestCase(label="some_holding_it", holdings=(True, False, True), expected=Agreement.SOME),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_group_reads_as_what_it_agrees_on(self, test_case: TestCase) -> None:
        assert Agreement.over(test_case.holdings) == test_case.expected


class TestWhatOneGestureSettlesTo(BaseTestSuite):
    """One gesture always moves a group, whichever reading it stood at."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: bool
        agreement: Agreement

    test_cases = (
        TestCase(label="from_none", agreement=Agreement.NONE, expected=True),
        TestCase(label="from_some", agreement=Agreement.SOME, expected=True),
        TestCase(label="from_all", agreement=Agreement.ALL, expected=False),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_a_gesture_settles_the_whole_group(self, test_case: TestCase) -> None:
        assert test_case.agreement.settles_to is test_case.expected
