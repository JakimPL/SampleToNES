from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Type, Union

import pytest

from sampletones.utils.common import first_key_for_value, next_power_of_two
from tests.sampletones.errors import expect_error


class TestNextPowerOfTwo:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        input_value: int
        expected_result: Union[int, type]
        test_id: str

    test_cases = [
        TestCase(input_value=0, expected_result=1, test_id="zero"),
        TestCase(input_value=1, expected_result=1, test_id="one"),
        TestCase(input_value=2, expected_result=2, test_id="already_power_of_two"),
        TestCase(input_value=3, expected_result=4, test_id="three"),
        TestCase(input_value=5, expected_result=8, test_id="five"),
        TestCase(input_value=7, expected_result=8, test_id="seven"),
        TestCase(input_value=8, expected_result=8, test_id="eight_power_of_two"),
        TestCase(input_value=9, expected_result=16, test_id="nine"),
        TestCase(input_value=15, expected_result=16, test_id="fifteen"),
        TestCase(input_value=16, expected_result=16, test_id="sixteen_power_of_two"),
        TestCase(input_value=17, expected_result=32, test_id="seventeen"),
        TestCase(input_value=100, expected_result=128, test_id="hundred"),
        TestCase(input_value=1000, expected_result=1024, test_id="thousand"),
        TestCase(input_value=1024, expected_result=1024, test_id="large_power_of_two"),
        TestCase(input_value=1025, expected_result=2048, test_id="just_over_power_of_two"),
        TestCase(input_value=1000000000, expected_result=1073741824, test_id="large_value"),
        TestCase(input_value=-1, expected_result=ValueError, test_id="negative_one"),
        TestCase(input_value=-5, expected_result=ValueError, test_id="negative_five"),
        TestCase(input_value=-100, expected_result=ValueError, test_id="negative_large"),
        TestCase(input_value=(1 << 64), expected_result=OverflowError, test_id="too_large_overflow"),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_next_power_of_two(self, test_case: TestNextPowerOfTwo.TestCase) -> None:
        if expect_error(next_power_of_two, test_case.expected_result, test_case.input_value):
            return

        result = next_power_of_two(test_case.input_value)
        assert result == test_case.expected_result
        assert type(result) == type(test_case.expected_result)


class TestFirstKeyForValue:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        dictionary: Any
        target: Any
        expected_result: Union[Optional[Any], Type[Exception]]
        test_id: str

    test_cases = [
        TestCase(
            dictionary={"a": 1, "b": 2, "c": 3},
            target=2,
            expected_result="b",
            test_id="value_found",
        ),
        TestCase(
            dictionary={"a": 1, "b": 2, "c": 3},
            target=5,
            expected_result=None,
            test_id="value_not_found",
        ),
        TestCase(
            dictionary={"a": 1, "b": 2, "c": 1},
            target=1,
            expected_result="a",
            test_id="duplicate_values_returns_first",
        ),
        TestCase(
            dictionary={},
            target=1,
            expected_result=None,
            test_id="empty_dictionary",
        ),
        TestCase(
            dictionary={"key": None, "other": "value"},
            target=None,
            expected_result="key",
            test_id="none_value",
        ),
        TestCase(
            dictionary={None: "value", "key": "other"},
            target="value",
            expected_result=None,
            test_id="none_key",
        ),
        TestCase(
            dictionary={"a": [1, 2], "b": [3, 4]},
            target=[1, 2],
            expected_result="a",
            test_id="list_value",
        ),
        TestCase(
            dictionary={1: "one", 2: "two", 3: "one"},
            target="one",
            expected_result=1,
            test_id="int_keys_with_duplicates",
        ),
        TestCase(
            dictionary={"x": False, "y": 0},
            target=0,
            expected_result="x",
            test_id="zero_and_false",
        ),
        TestCase(
            dictionary={"x": 1, "y": True},
            target=1,
            expected_result="x",
            test_id="one_and_true",
        ),
        TestCase(
            dictionary="not_a_dict",
            target=1,
            expected_result=TypeError,
            test_id="not_a_dictionary",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_first_key_for_value(self, test_case: TestFirstKeyForValue.TestCase) -> None:
        if expect_error(
            first_key_for_value,
            test_case.expected_result,
            test_case.dictionary,
            test_case.target,
        ):
            return

        result = first_key_for_value(test_case.dictionary, test_case.target)
        assert result == test_case.expected_result
