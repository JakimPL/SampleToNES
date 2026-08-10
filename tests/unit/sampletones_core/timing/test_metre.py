from dataclasses import dataclass
from typing import Tuple

import pytest

from sampletones_core.timing.metre import Metre
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase


class TestSpans(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: Tuple[Tuple[int, ...], ...]
        rows: int
        first_highlight: int
        second_highlight: int

        @property
        def label(self) -> str:
            return f"{self.rows}_rows_at_{self.first_highlight}_{self.second_highlight}"

    test_cases = (
        TestCase(
            rows=16,
            first_highlight=4,
            second_highlight=16,
            expected=((4, 4, 4, 4),),
        ),
        TestCase(
            rows=64,
            first_highlight=4,
            second_highlight=16,
            expected=((4, 4, 4, 4), (4, 4, 4, 4), (4, 4, 4, 4), (4, 4, 4, 4)),
        ),
        TestCase(
            rows=60,
            first_highlight=4,
            second_highlight=16,
            expected=((4, 4, 4, 4), (4, 4, 4, 4), (4, 4, 4, 4), (4, 4, 4)),
        ),
        TestCase(
            rows=17,
            first_highlight=4,
            second_highlight=16,
            expected=((4, 4, 4, 4), (1,)),
        ),
        TestCase(
            rows=12,
            first_highlight=3,
            second_highlight=12,
            expected=((3, 3, 3, 3),),
        ),
        TestCase(
            rows=16,
            first_highlight=6,
            second_highlight=12,
            expected=((6, 6), (4,)),
        ),
        TestCase(
            rows=1,
            first_highlight=4,
            second_highlight=16,
            expected=((1,),),
        ),
        TestCase(
            rows=8,
            first_highlight=1,
            second_highlight=1,
            expected=((1,), (1,), (1,), (1,), (1,), (1,), (1,), (1,)),
        ),
        TestCase(
            rows=8,
            first_highlight=16,
            second_highlight=4,
            expected=((4,), (4,)),
        ),
        TestCase(
            rows=8,
            first_highlight=64,
            second_highlight=64,
            expected=((8,),),
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_spans_match(self, test_case: TestCase) -> None:
        metre = Metre(
            rows=test_case.rows,
            first_highlight=test_case.first_highlight,
            second_highlight=test_case.second_highlight,
        )
        assert metre.spans == test_case.expected

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_spans_cover_the_pattern(self, test_case: TestCase) -> None:
        metre = Metre(
            rows=test_case.rows,
            first_highlight=test_case.first_highlight,
            second_highlight=test_case.second_highlight,
        )
        assert sum(sum(beats) for beats in metre.spans) == test_case.rows


class TestBounds(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: str
        field: str

        @property
        def label(self) -> str:
            return f"{self.field}_below_one"

    test_cases = (
        TestCase(
            field="rows",
            expected="rows must be at least 1",
        ),
        TestCase(
            field="first_highlight",
            expected="first_highlight must be at least 1",
        ),
        TestCase(
            field="second_highlight",
            expected="second_highlight must be at least 1",
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_field_below_one_is_rejected(self, test_case: TestCase) -> None:
        fields = {"rows": 16, "first_highlight": 4, "second_highlight": 16, test_case.field: 0}
        with pytest.raises(ValueError, match=test_case.expected):
            Metre(**fields)
