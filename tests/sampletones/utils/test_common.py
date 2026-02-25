from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Type, Union

import pytest

from sampletones.utils.common import first_key_for_value, next_power_of_two
from tests.sampletones.errors import expect_error
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


class TestNextPowerOfTwo(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[int, type]
        input_value: int

    test_cases = [
        TestCase(input_value=0, expected=1, label="zero"),
        TestCase(input_value=1, expected=1, label="one"),
        TestCase(input_value=2, expected=2, label="already_power_of_two"),
        TestCase(input_value=3, expected=4, label="three"),
        TestCase(input_value=5, expected=8, label="five"),
        TestCase(input_value=7, expected=8, label="seven"),
        TestCase(input_value=8, expected=8, label="eight_power_of_two"),
        TestCase(input_value=9, expected=16, label="nine"),
        TestCase(input_value=15, expected=16, label="fifteen"),
        TestCase(input_value=16, expected=16, label="sixteen_power_of_two"),
        TestCase(input_value=17, expected=32, label="seventeen"),
        TestCase(input_value=100, expected=128, label="hundred"),
        TestCase(input_value=1000, expected=1024, label="thousand"),
        TestCase(input_value=1024, expected=1024, label="large_power_of_two"),
        TestCase(input_value=1025, expected=2048, label="just_over_power_of_two"),
        TestCase(input_value=1000000000, expected=1073741824, label="large_value"),
        TestCase(input_value=-1, expected=ValueError, label="negative_one"),
        TestCase(input_value=-5, expected=ValueError, label="negative_five"),
        TestCase(input_value=-100, expected=ValueError, label="negative_large"),
        TestCase(input_value=(1 << 64), expected=OverflowError, label="too_large_overflow"),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_next_power_of_two(self, test_case: TestCase) -> None:
        if expect_error(next_power_of_two, test_case.expected, test_case.input_value):
            return

        result = next_power_of_two(test_case.input_value)
        assert result == test_case.expected
        assert type(result) == type(test_case.expected)


class TestFirstKeyForValue(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[Optional[Any], Type[Exception]]
        dictionary: Any
        target: Any

    test_cases = [
        TestCase(
            dictionary={"a": 1, "b": 2, "c": 3},
            target=2,
            expected="b",
            label="value_found",
        ),
        TestCase(
            dictionary={"a": 1, "b": 2, "c": 3},
            target=5,
            expected=None,
            label="value_not_found",
        ),
        TestCase(
            dictionary={"a": 1, "b": 2, "c": 1},
            target=1,
            expected="a",
            label="duplicate_values_returns_first",
        ),
        TestCase(
            dictionary={},
            target=1,
            expected=None,
            label="empty_dictionary",
        ),
        TestCase(
            dictionary={"key": None, "other": "value"},
            target=None,
            expected="key",
            label="none_value",
        ),
        TestCase(
            dictionary={None: "value", "key": "other"},
            target="value",
            expected=None,
            label="none_key",
        ),
        TestCase(
            dictionary={"a": [1, 2], "b": [3, 4]},
            target=[1, 2],
            expected="a",
            label="list_value",
        ),
        TestCase(
            dictionary={1: "one", 2: "two", 3: "one"},
            target="one",
            expected=1,
            label="int_keys_with_duplicates",
        ),
        TestCase(
            dictionary={"x": False, "y": 0},
            target=0,
            expected="x",
            label="zero_and_false",
        ),
        TestCase(
            dictionary={"x": 1, "y": True},
            target=1,
            expected="x",
            label="one_and_true",
        ),
        TestCase(
            dictionary="not_a_dict",
            target=1,
            expected=TypeError,
            label="not_a_dictionary",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_first_key_for_value(self, test_case: TestCase) -> None:
        if expect_error(
            first_key_for_value,
            test_case.expected,
            test_case.dictionary,
            test_case.target,
        ):
            return

        result = first_key_for_value(test_case.dictionary, test_case.target)
        assert result == test_case.expected
