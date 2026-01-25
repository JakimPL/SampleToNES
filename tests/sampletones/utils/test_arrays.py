from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Type, Union

import numpy as np
import pytest

from sampletones import xp
from sampletones.types.array import DTypeLike
from sampletones.utils.arrays import clamp, infer_dtype, isnan, pad, trim
from tests.sampletones.errors import expect_error


class TestIsnan:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        value: Any
        expected_result: Union[bool, Type[Exception]]
        test_id: str

    @pytest.mark.parametrize(
        "test_case",
        [
            TestCase(
                value=None,
                expected_result=True,
                test_id="none_is_nan",
            ),
            TestCase(
                value=float("nan"),
                expected_result=True,
                test_id="builtin_float_nan",
            ),
            TestCase(
                value=float("inf"),
                expected_result=False,
                test_id="builtin_float_inf",
            ),
            TestCase(
                value=float("-inf"),
                expected_result=False,
                test_id="builtin_float_neg_inf",
            ),
            TestCase(
                value=0.0,
                expected_result=False,
                test_id="builtin_float_zero",
            ),
            TestCase(
                value=1.5,
                expected_result=False,
                test_id="builtin_float_normal",
            ),
            TestCase(
                value=0,
                expected_result=False,
                test_id="builtin_int_zero",
            ),
            TestCase(
                value=42,
                expected_result=False,
                test_id="builtin_int_positive",
            ),
            TestCase(
                value=-17,
                expected_result=False,
                test_id="builtin_int_negative",
            ),
            TestCase(
                value=True,
                expected_result=False,
                test_id="builtin_bool_true",
            ),
            TestCase(
                value=False,
                expected_result=False,
                test_id="builtin_bool_false",
            ),
            TestCase(
                value=np.nan,
                expected_result=True,
                test_id="numpy_nan",
            ),
            TestCase(
                value=np.inf,
                expected_result=False,
                test_id="numpy_inf",
            ),
            TestCase(
                value=np.float32(np.nan),
                expected_result=True,
                test_id="numpy_float32_nan",
            ),
            TestCase(
                value=np.float64(np.nan),
                expected_result=True,
                test_id="numpy_float64_nan",
            ),
            TestCase(
                value=np.float32(3.14),
                expected_result=False,
                test_id="numpy_float32_normal",
            ),
            TestCase(
                value=np.float64(2.718),
                expected_result=False,
                test_id="numpy_float64_normal",
            ),
            TestCase(
                value=np.int32(100),
                expected_result=False,
                test_id="numpy_int32",
            ),
            TestCase(
                value=np.int64(-256),
                expected_result=False,
                test_id="numpy_int64",
            ),
            TestCase(
                value=np.int8(5),
                expected_result=False,
                test_id="numpy_int8",
            ),
            TestCase(
                value=np.uint16(1000),
                expected_result=False,
                test_id="numpy_uint16",
            ),
            TestCase(
                value=xp.nan,
                expected_result=True,
                test_id="xp_nan",
            ),
            TestCase(
                value=xp.float32(xp.inf),
                expected_result=False,
                test_id="xp_float32_inf",
            ),
            TestCase(
                value=xp.float64(42.0),
                expected_result=False,
                test_id="xp_float64_normal",
            ),
            TestCase(
                value=xp.int32(7),
                expected_result=False,
                test_id="xp_int32",
            ),
            TestCase(
                value="nan",
                expected_result=TypeError,
                test_id="string_raises_type_error",
            ),
            TestCase(
                value=[1, 2, 3],
                expected_result=TypeError,
                test_id="list_raises_type_error",
            ),
            TestCase(
                value={"key": "value"},
                expected_result=TypeError,
                test_id="dict_raises_type_error",
            ),
            TestCase(
                value=np.array(["a", "b"], dtype=object),
                expected_result=TypeError,
                test_id="numpy_string_object_array_raises_type_error",
            ),
        ],
        ids=lambda tc: tc.test_id,
    )
    def test_isnan(self, test_case: TestIsnan.TestCase) -> None:
        if expect_error(isnan, test_case.expected_result, test_case.value):
            return

        result = isnan(test_case.value)
        assert result == test_case.expected_result


class TestInferDtype:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        value: Any
        dtype: Any
        expected_result: Union[DTypeLike, Type[Exception]]
        test_id: str

    test_cases = [
        TestCase(
            value=None,
            dtype=np.int32,
            expected_result=np.float32,
            test_id="none_returns_float32",
        ),
        TestCase(
            value=42,
            dtype=np.int32,
            expected_result=np.int32,
            test_id="builtin_int_with_int32_dtype",
        ),
        TestCase(
            value=3.14,
            dtype=np.float64,
            expected_result=np.float64,
            test_id="builtin_float_with_float64_dtype",
        ),
        TestCase(
            value=float("nan"),
            dtype=np.int32,
            expected_result=np.float32,
            test_id="builtin_nan_with_int_dtype_returns_float32",
        ),
        TestCase(
            value=float("nan"),
            dtype=np.float64,
            expected_result=np.float64,
            test_id="builtin_nan_with_float64_dtype_preserves",
        ),
        TestCase(
            value=float("inf"),
            dtype=np.int32,
            expected_result=np.float32,
            test_id="builtin_inf_with_int_dtype_returns_float32",
        ),
        TestCase(
            value=float("inf"),
            dtype=np.float32,
            expected_result=np.float32,
            test_id="builtin_inf_with_float32_dtype_preserves",
        ),
        TestCase(
            value=float("-inf"),
            dtype=np.int64,
            expected_result=np.float32,
            test_id="builtin_neg_inf_with_int_dtype_returns_float32",
        ),
        TestCase(
            value=True,
            dtype=np.bool_,
            expected_result=np.bool_,
            test_id="builtin_bool_with_bool_dtype",
        ),
        TestCase(
            value=False,
            dtype=np.int8,
            expected_result=np.int8,
            test_id="builtin_bool_false_with_int8_dtype",
        ),
        TestCase(
            value=np.int32(100),
            dtype=np.int32,
            expected_result=np.int32,
            test_id="numpy_int32_with_int32_dtype",
        ),
        TestCase(
            value=np.float64(2.718),
            dtype=np.float64,
            expected_result=np.float64,
            test_id="numpy_float64_with_float64_dtype",
        ),
        TestCase(
            value=np.nan,
            dtype=np.int32,
            expected_result=np.float32,
            test_id="numpy_nan_with_int_dtype_returns_float32",
        ),
        TestCase(
            value=np.nan,
            dtype=np.float64,
            expected_result=np.float64,
            test_id="numpy_nan_with_float64_dtype_preserves",
        ),
        TestCase(
            value=np.inf,
            dtype=np.int64,
            expected_result=np.float32,
            test_id="numpy_inf_with_int_dtype_returns_float32",
        ),
        TestCase(
            value=np.inf,
            dtype=np.float32,
            expected_result=np.float32,
            test_id="numpy_inf_with_float32_dtype_preserves",
        ),
        TestCase(
            value=np.float32(1.5),
            dtype=np.int16,
            expected_result=np.int16,
            test_id="numpy_float32_finite_with_int_dtype_preserves",
        ),
        TestCase(
            value=np.int8(7),
            dtype=np.float64,
            expected_result=np.float64,
            test_id="numpy_int8_with_float64_dtype",
        ),
        TestCase(
            value=np.uint32(500),
            dtype=np.uint32,
            expected_result=np.uint32,
            test_id="numpy_uint32_with_uint32_dtype",
        ),
        TestCase(
            value=xp.int32(42),
            dtype=xp.int32,
            expected_result=xp.int32,
            test_id="xp_int_with_int32_dtype",
        ),
        TestCase(
            value=xp.float64(3.14),
            dtype=xp.float64,
            expected_result=xp.float64,
            test_id="xp_float64_with_float64_dtype",
        ),
        TestCase(
            value=xp.nan,
            dtype=xp.int32,
            expected_result=xp.float32,
            test_id="xp_nan_with_int_dtype_returns_float32",
        ),
        TestCase(
            value=xp.inf,
            dtype=xp.float64,
            expected_result=xp.float64,
            test_id="xp_inf_with_float64_dtype_preserves",
        ),
        TestCase(
            value=xp.int64(-999),
            dtype=xp.int64,
            expected_result=xp.int64,
            test_id="xp_int64_with_int64_dtype",
        ),
        TestCase(
            value="42",
            dtype=np.int32,
            expected_result=TypeError,
            test_id="string_raises_type_error",
        ),
        TestCase(
            value=[1, 2, 3],
            dtype=np.int32,
            expected_result=TypeError,
            test_id="list_raises_type_error",
        ),
        TestCase(
            value={"key": 42},
            dtype=np.float32,
            expected_result=TypeError,
            test_id="dict_raises_type_error",
        ),
        TestCase(
            value=np.array(["hello", "world"], dtype=object),
            dtype=np.int32,
            expected_result=TypeError,
            test_id="numpy_string_object_array_raises_type_error",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_infer_dtype(self, test_case: TestInferDtype.TestCase) -> None:
        if expect_error(infer_dtype, test_case.expected_result, test_case.value, test_case.dtype):
            return

        result = infer_dtype(test_case.value, test_case.dtype)
        assert result == test_case.expected_result


class TestClamp:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        value: Any
        min_value: Any
        max_value: Any
        expected_result: Union[int, float, Type[Exception]]
        test_id: str

    test_cases = [
        TestCase(
            value=5,
            min_value=0,
            max_value=10,
            expected_result=5,
            test_id="int_within_range",
        ),
        TestCase(
            value=-5,
            min_value=0,
            max_value=10,
            expected_result=0,
            test_id="int_below_min",
        ),
        TestCase(
            value=15,
            min_value=0,
            max_value=10,
            expected_result=10,
            test_id="int_above_max",
        ),
        TestCase(
            value=0,
            min_value=0,
            max_value=10,
            expected_result=0,
            test_id="int_equals_min",
        ),
        TestCase(
            value=10,
            min_value=0,
            max_value=10,
            expected_result=10,
            test_id="int_equals_max",
        ),
        TestCase(
            value=5.5,
            min_value=0.0,
            max_value=10.0,
            expected_result=5.5,
            test_id="float_within_range",
        ),
        TestCase(
            value=-2.5,
            min_value=0.0,
            max_value=10.0,
            expected_result=0.0,
            test_id="float_below_min",
        ),
        TestCase(
            value=12.7,
            min_value=0.0,
            max_value=10.0,
            expected_result=10.0,
            test_id="float_above_max",
        ),
        TestCase(
            value=0.0,
            min_value=0.0,
            max_value=10.0,
            expected_result=0.0,
            test_id="float_equals_min",
        ),
        TestCase(
            value=10.0,
            min_value=0.0,
            max_value=10.0,
            expected_result=10.0,
            test_id="float_equals_max",
        ),
        TestCase(
            value=-100,
            min_value=-50,
            max_value=-10,
            expected_result=-50,
            test_id="negative_range_below",
        ),
        TestCase(
            value=-30,
            min_value=-50,
            max_value=-10,
            expected_result=-30,
            test_id="negative_range_within",
        ),
        TestCase(
            value=0,
            min_value=-50,
            max_value=-10,
            expected_result=-10,
            test_id="negative_range_above",
        ),
        TestCase(
            value=np.int32(5),
            min_value=np.int32(0),
            max_value=np.int32(10),
            expected_result=5,
            test_id="numpy_int32_all",
        ),
        TestCase(
            value=np.int64(5),
            min_value=np.int64(0),
            max_value=np.int64(10),
            expected_result=5,
            test_id="numpy_int64_all",
        ),
        TestCase(
            value=np.float32(5.5),
            min_value=np.float32(0.0),
            max_value=np.float32(10.0),
            expected_result=5.5,
            test_id="numpy_float32_all",
        ),
        TestCase(
            value=np.float64(5.5),
            min_value=np.float64(0.0),
            max_value=np.float64(10.0),
            expected_result=5.5,
            test_id="numpy_float64_all",
        ),
        TestCase(
            value=np.int64(5),
            min_value=0,
            max_value=10,
            expected_result=5,
            test_id="numpy_int_with_python_int_bounds",
        ),
        TestCase(
            value=5,
            min_value=np.int32(0),
            max_value=np.int64(10),
            expected_result=5,
            test_id="python_int_with_numpy_int_bounds",
        ),
        TestCase(
            value=5,
            min_value=0.0,
            max_value=10.0,
            expected_result=5.0,
            test_id="int_value_with_float_bounds_promotes_to_float",
        ),
        TestCase(
            value=5.0,
            min_value=0,
            max_value=10,
            expected_result=5.0,
            test_id="float_value_with_int_bounds_stays_float",
        ),
        TestCase(
            value=5,
            min_value=0.5,
            max_value=10,
            expected_result=5.0,
            test_id="mixed_types_int_value_float_min",
        ),
        TestCase(
            value=5,
            min_value=0,
            max_value=10.5,
            expected_result=5.0,
            test_id="mixed_types_int_value_float_max",
        ),
        TestCase(
            value=np.int32(5),
            min_value=0.0,
            max_value=10.0,
            expected_result=5.0,
            test_id="numpy_int_with_float_bounds",
        ),
        TestCase(
            value=np.float32(5.5),
            min_value=0,
            max_value=10,
            expected_result=5.5,
            test_id="numpy_float_with_int_bounds",
        ),
        TestCase(
            value=5,
            min_value=7,
            max_value=7,
            expected_result=7,
            test_id="strict_bounds_int_equal",
        ),
        TestCase(
            value=12.0,
            min_value=7.0,
            max_value=7.0,
            expected_result=7.0,
            test_id="strict_bounds_float_equal",
        ),
        TestCase(
            value=5,
            min_value=0,
            max_value=0,
            expected_result=0,
            test_id="strict_bounds_zero_int",
        ),
        TestCase(
            value=5.0,
            min_value=0.0,
            max_value=0.0,
            expected_result=0.0,
            test_id="strict_bounds_zero_float",
        ),
        TestCase(
            value=5,
            min_value=0,
            max_value=0.0,
            expected_result=0.0,
            test_id="strict_bounds_zero_mixed_int_float",
        ),
        TestCase(
            value=5.0,
            min_value=0,
            max_value=0.0,
            expected_result=0.0,
            test_id="strict_bounds_zero_mixed_float",
        ),
        TestCase(
            value=5,
            min_value=10,
            max_value=0,
            expected_result=0,
            test_id="inverted_bounds_max_takes_precedence",
        ),
        TestCase(
            value=15,
            min_value=20,
            max_value=10,
            expected_result=10,
            test_id="inverted_bounds_value_between",
        ),
        TestCase(
            value=25,
            min_value=20,
            max_value=10,
            expected_result=10,
            test_id="inverted_bounds_value_above_both",
        ),
        TestCase(
            value=5,
            min_value=None,
            max_value=10,
            expected_result=5,
            test_id="none_min_within_max",
        ),
        TestCase(
            value=5,
            min_value=None,
            max_value=3,
            expected_result=3,
            test_id="none_min_above_max",
        ),
        TestCase(
            value=5,
            min_value=7,
            max_value=None,
            expected_result=7,
            test_id="none_max_below_min",
        ),
        TestCase(
            value=5,
            min_value=3,
            max_value=None,
            expected_result=5,
            test_id="none_max_above_min",
        ),
        TestCase(
            value=5,
            min_value=None,
            max_value=None,
            expected_result=5,
            test_id="both_bounds_none",
        ),
        TestCase(
            value=5.5,
            min_value=None,
            max_value=None,
            expected_result=5.5,
            test_id="both_bounds_none_float",
        ),
        TestCase(
            value=float("inf"),
            min_value=0.0,
            max_value=100.0,
            expected_result=100.0,
            test_id="positive_infinity_clamped_to_max",
        ),
        TestCase(
            value=float("-inf"),
            min_value=0.0,
            max_value=100.0,
            expected_result=0.0,
            test_id="negative_infinity_clamped_to_min",
        ),
        TestCase(
            value=5.0,
            min_value=float("-inf"),
            max_value=100.0,
            expected_result=5.0,
            test_id="neg_inf_min_bound",
        ),
        TestCase(
            value=5.0,
            min_value=0.0,
            max_value=float("inf"),
            expected_result=5.0,
            test_id="pos_inf_max_bound",
        ),
        TestCase(
            value=float("inf"),
            min_value=float("-inf"),
            max_value=float("inf"),
            expected_result=float("inf"),
            test_id="inf_value_inf_bounds",
        ),
        TestCase(
            value=1.0,
            min_value=0.0,
            max_value=float("-inf"),
            expected_result=float("-inf"),
            test_id="max_precedence_with_neg_inf",
        ),
        TestCase(
            value=float("nan"),
            min_value=0.0,
            max_value=10.0,
            expected_result=float("nan"),
            test_id="nan_value_with_bounds",
        ),
        TestCase(
            value=5.0,
            min_value=float("nan"),
            max_value=10.0,
            expected_result=5.0,
            test_id="nan_min_bound",
        ),
        TestCase(
            value=5.0,
            min_value=7.0,
            max_value=float("nan"),
            expected_result=7.0,
            test_id="nan_max_bound",
        ),
        TestCase(
            value=np.nan,
            min_value=0.0,
            max_value=10.0,
            expected_result=float("nan"),
            test_id="numpy_nan_value",
        ),
        TestCase(
            value="5",
            min_value=0,
            max_value=10,
            expected_result=TypeError,
            test_id="string_value",
        ),
        TestCase(
            value=5,
            min_value="0",
            max_value=10,
            expected_result=TypeError,
            test_id="string_min_bound",
        ),
        TestCase(
            value=5,
            min_value=0,
            max_value="10",
            expected_result=TypeError,
            test_id="string_max_bound",
        ),
        TestCase(
            value=[5],
            min_value=0,
            max_value=10,
            expected_result=TypeError,
            test_id="list_value",
        ),
        TestCase(
            value=None,
            min_value=0,
            max_value=10,
            expected_result=TypeError,
            test_id="none_value",
        ),
        TestCase(
            value=5,
            min_value=[0],
            max_value=10,
            expected_result=TypeError,
            test_id="list_min_bound",
        ),
        TestCase(
            value=5,
            min_value=0,
            max_value={"max": 10},
            expected_result=TypeError,
            test_id="dict_max_bound",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_clamp(self, test_case: TestClamp.TestCase) -> None:
        if expect_error(
            clamp,
            test_case.expected_result,
            test_case.value,
            test_case.min_value,
            test_case.max_value,
        ):
            return

        result = clamp(test_case.value, test_case.min_value, test_case.max_value)
        assert type(result) == type(test_case.expected_result)
        if isinstance(test_case.expected_result, float) and math.isnan(test_case.expected_result):
            assert math.isnan(result)
        else:
            assert result == test_case.expected_result


class TestPad:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        array: Any
        left: Any
        right: Any
        value: Any
        expected_result: Union[np.ndarray, Type[Exception]]
        test_id: str

    test_cases = [
        TestCase(
            array=np.array([], dtype=np.int64),
            left=0,
            right=0,
            value=0,
            expected_result=np.array([], dtype=np.int64),
            test_id="empty_int_array_empty_padding",
        ),
        TestCase(
            array=np.array([], dtype=np.float32),
            left=0,
            right=0,
            value=0,
            expected_result=np.array([], dtype=np.float32),
            test_id="empty_float_array_empty_padding",
        ),
        TestCase(
            array=np.array([-1], dtype=np.int64),
            left=0,
            right=0,
            value=0,
            expected_result=np.array([], dtype=np.int64),
            test_id="nonempty_array_empty_padding",
        ),
        TestCase(
            array=np.array([1, 2, 3, 4, 5], dtype=np.int64),
            left=0,
            right=5,
            value=0,
            expected_result=np.array([1, 2, 3, 4, 5], dtype=np.int64),
            test_id="no_padding",
        ),
        TestCase(
            array=np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64),
            left=-2,
            right=5,
            value=0,
            expected_result=np.array([0.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64),
            test_id="left_padding_only",
        ),
        TestCase(
            array=np.array([1, 2, 3, 4, 5]),
            left=0,
            right=7,
            value=0,
            expected_result=np.array([1, 2, 3, 4, 5, 0, 0]),
            test_id="right_padding_only",
        ),
        TestCase(
            array=np.array([1, 2, 3, 4, 5]),
            left=-2,
            right=7,
            value=0,
            expected_result=np.array([0, 0, 1, 2, 3, 4, 5, 0, 0]),
            test_id="both_sides_padding",
        ),
        TestCase(
            array=np.array([1, 2, 3, 4, 5]),
            left=1,
            right=4,
            value=0,
            expected_result=np.array([2, 3, 4]),
            test_id="slice_middle",
        ),
        TestCase(
            array=np.array([1, 2, 3, 4, 5]),
            left=3,
            right=8,
            value=0,
            expected_result=np.array([4, 5, 0, 0, 0]),
            test_id="slice_end_with_padding",
        ),
        TestCase(
            array=np.array([1, 2, 3, 4, 5]),
            left=-5,
            right=-2,
            value=9,
            expected_result=np.array([9, 9, 9]),
            test_id="negative_indices_with_custom_value",
        ),
        TestCase(
            array=np.array([1, 2, 3, 4, 5]),
            left=10,
            right=15,
            value=7,
            expected_result=np.array([7, 7, 7, 7, 7]),
            test_id="completely_outside_right",
        ),
        TestCase(
            array=np.array([1, 2, 3], dtype=np.int64),
            left=-1,
            right=4,
            value=np.nan,
            expected_result=np.array([np.nan, 1.0, 2.0, 3.0, np.nan], dtype=np.float32),
            test_id="float_array_with_nan_padding_changes_dtype",
        ),
        TestCase(
            array=np.array([[1.5, 2.5, 3.5]]),
            left=-1,
            right=4,
            value=np.nan,
            expected_result=ValueError,
            test_id="array_not_1d",
        ),
        TestCase(
            array=[1, 2, 3],
            left=1,
            right=2,
            value=0,
            expected_result=TypeError,
            test_id="list_not_array",
        ),
        TestCase(
            array=np.array([1, 2, 3], dtype=np.int16),
            left=1,
            right=2,
            value=0,
            expected_result=np.array([2], dtype=np.int16),
            test_id="preservers_dtype_int16",
        ),
        TestCase(
            array=np.array([1, 2, 3], dtype=np.int64),
            left=None,
            right=2,
            value=0,
            expected_result=TypeError,
            test_id="invalid_left_padding_none",
        ),
        TestCase(
            array=np.array([1, 2, 3], dtype=np.int64),
            left=1,
            right=None,
            value=0,
            expected_result=TypeError,
            test_id="invalid_right_padding_none",
        ),
        TestCase(
            array=np.array([1, 2, 3], dtype=np.int64),
            left=1.0,
            right=2,
            value=0,
            expected_result=TypeError,
            test_id="invalid_left_padding_float",
        ),
        TestCase(
            array=np.array([1, 2, 3], dtype=np.int64),
            left=3,
            right=2,
            value=0,
            expected_result=ValueError,
            test_id="out_of_order_padding",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_pad(self, test_case: TestPad.TestCase) -> None:
        if expect_error(
            pad,
            test_case.expected_result,
            test_case.array,
            test_case.left,
            test_case.right,
            test_case.value,
        ):
            return

        assert isinstance(test_case.expected_result, np.ndarray)
        result = pad(test_case.array, test_case.left, test_case.right, test_case.value)
        np.testing.assert_array_equal(result, test_case.expected_result)
        assert result.dtype == test_case.expected_result.dtype


class TestTrim:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        input_array: Any
        expected_result: Union[np.ndarray, Type[Exception]]
        test_id: str

    test_cases = [
        TestCase(
            input_array=np.array([1, 1, 2, 2, 3, 3, 3, 3]),
            expected_result=np.array([1, 1, 2, 2, 3]),
            test_id="trailing_duplicates",
        ),
        TestCase(
            input_array=np.array([5, 5, 5, 5]),
            expected_result=np.array([5]),
            test_id="all_same_values",
        ),
        TestCase(
            input_array=np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
            expected_result=np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
            test_id="no_duplicates",
        ),
        TestCase(
            input_array=np.array([1, 1, 1, 2, 3, 3]),
            expected_result=np.array([1, 1, 1, 2, 3]),
            test_id="duplicates_at_start_and_end",
        ),
        TestCase(
            input_array=np.array([1, 2, 1, 2, 1, 1]),
            expected_result=np.array([1, 2, 1, 2, 1]),
            test_id="alternating_with_trailing_dup",
        ),
        TestCase(
            input_array=np.array([7]),
            expected_result=np.array([7]),
            test_id="single_element",
        ),
        TestCase(
            input_array=np.array([1, 2, 2, 2, 2, 2]),
            expected_result=np.array([1, 2]),
            test_id="many_trailing_duplicates",
        ),
        TestCase(
            input_array=np.array([0, 0, 1, 1, 0, 0, 0]),
            expected_result=np.array([0, 0, 1, 1, 0]),
            test_id="zero_values_with_trailing_dups",
        ),
        TestCase(
            input_array=np.array([[1, 2]]),
            expected_result=ValueError,
            test_id="not_1d_array",
        ),
        TestCase(
            input_array=[1, 2],
            expected_result=TypeError,
            test_id="not_an_array",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_trim(self, test_case: TestTrim.TestCase) -> None:
        if expect_error(trim, test_case.expected_result, test_case.input_array):
            return

        result = trim(test_case.input_array)
        np.testing.assert_array_equal(result, test_case.expected_result)
