from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Type, Union

import numpy as np
import pytest

from sampletones_core.array import xp
from sampletones_shared.types.array import DTypeLike
from sampletones_shared.utils.arrays import (
    cast_to_float,
    clamp,
    infer_dtype,
    is_increasing,
    isfinite,
    isnan,
    pad,
    trim,
)
from tests.suite.arrays import assert_array_equal
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.errors import expect_error


class TestIsnan(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[bool, Type[Exception]]
        value: Any

    test_cases = [
        TestCase(
            value=None,
            expected=True,
            label="none_is_nan",
        ),
        TestCase(
            value=float("nan"),
            expected=True,
            label="builtin_float_nan",
        ),
        TestCase(
            value=float("inf"),
            expected=False,
            label="builtin_float_inf",
        ),
        TestCase(
            value=float("-inf"),
            expected=False,
            label="builtin_float_neg_inf",
        ),
        TestCase(
            value=0.0,
            expected=False,
            label="builtin_float_zero",
        ),
        TestCase(
            value=1.5,
            expected=False,
            label="builtin_float_normal",
        ),
        TestCase(
            value=0,
            expected=False,
            label="builtin_int_zero",
        ),
        TestCase(
            value=42,
            expected=False,
            label="builtin_int_positive",
        ),
        TestCase(
            value=-17,
            expected=False,
            label="builtin_int_negative",
        ),
        TestCase(
            value=True,
            expected=False,
            label="builtin_bool_true",
        ),
        TestCase(
            value=False,
            expected=False,
            label="builtin_bool_false",
        ),
        TestCase(
            value=np.nan,
            expected=True,
            label="numpy_nan",
        ),
        TestCase(
            value=np.inf,
            expected=False,
            label="numpy_inf",
        ),
        TestCase(
            value=np.float32(np.nan),
            expected=True,
            label="numpy_float32_nan",
        ),
        TestCase(
            value=np.float64(np.nan),
            expected=True,
            label="numpy_float64_nan",
        ),
        TestCase(
            value=np.float32(3.14),
            expected=False,
            label="numpy_float32_normal",
        ),
        TestCase(
            value=np.float64(2.718),
            expected=False,
            label="numpy_float64_normal",
        ),
        TestCase(
            value=np.int32(100),
            expected=False,
            label="numpy_int32",
        ),
        TestCase(
            value=np.int64(-256),
            expected=False,
            label="numpy_int64",
        ),
        TestCase(
            value=np.int8(5),
            expected=False,
            label="numpy_int8",
        ),
        TestCase(
            value=np.uint16(1000),
            expected=False,
            label="numpy_uint16",
        ),
        TestCase(
            value=xp.nan,
            expected=True,
            label="xp_nan",
        ),
        TestCase(
            value=xp.float32(xp.inf),
            expected=False,
            label="xp_float32_inf",
        ),
        TestCase(
            value=xp.float64(42.0),
            expected=False,
            label="xp_float64_normal",
        ),
        TestCase(
            value=xp.int32(7),
            expected=False,
            label="xp_int32",
        ),
        TestCase(
            value="nan",
            expected=TypeError,
            label="string_raises_type_error",
        ),
        TestCase(
            value=[1, 2, 3],
            expected=TypeError,
            label="list_raises_type_error",
        ),
        TestCase(
            value={"key": "value"},
            expected=TypeError,
            label="dict_raises_type_error",
        ),
        TestCase(
            value=np.array(["a", "b"], dtype=object),
            expected=TypeError,
            label="numpy_string_object_array_raises_type_error",
        ),
        TestCase(
            value=np.array([1.0, 2.0, 3.0], dtype=np.float32),
            expected=False,
            label="array_float32_all_finite_not_nan",
        ),
        TestCase(
            value=np.array([1.0, np.nan, 3.0], dtype=np.float32),
            expected=False,
            label="array_float32_with_nan_not_all_nan",
        ),
        TestCase(
            value=np.array([np.nan, np.nan, np.nan], dtype=np.float32),
            expected=True,
            label="array_float32_all_nan",
        ),
        TestCase(
            value=np.array([1.0, np.inf, -np.inf], dtype=np.float32),
            expected=False,
            label="array_float32_with_inf_not_nan",
        ),
        TestCase(
            value=np.array([np.nan, np.inf, -np.inf, 0.0], dtype=np.float32),
            expected=False,
            label="array_float32_mixed_not_all_nan",
        ),
        TestCase(
            value=np.array([1.0, 2.0, 3.0], dtype=np.float64),
            expected=False,
            label="array_float64_all_finite_not_nan",
        ),
        TestCase(
            value=np.array([1.0, np.nan, 3.0], dtype=np.float64),
            expected=False,
            label="array_float64_with_nan_not_all_nan",
        ),
        TestCase(
            value=np.array([np.nan, np.nan], dtype=np.float64),
            expected=True,
            label="array_float64_all_nan",
        ),
        TestCase(
            value=np.array([np.inf, -np.inf, 5.0], dtype=np.float64),
            expected=False,
            label="array_float64_with_inf_not_nan",
        ),
        TestCase(
            value=np.array([1, 2, 3], dtype=np.int32),
            expected=False,
            label="array_int32_not_nan",
        ),
        TestCase(
            value=np.array([0, -5, 100], dtype=np.int64),
            expected=False,
            label="array_int64_not_nan",
        ),
        TestCase(
            value=np.array([1, 2], dtype=np.int8),
            expected=False,
            label="array_int8_not_nan",
        ),
        TestCase(
            value=np.array([100, 200], dtype=np.uint16),
            expected=False,
            label="array_uint16_not_nan",
        ),
        TestCase(
            value=np.array([], dtype=np.float32),
            expected=True,
            label="array_empty_float32_all_nan",
        ),
        TestCase(
            value=np.array([], dtype=np.int64),
            expected=True,
            label="array_empty_int64_all_nan",
        ),
        TestCase(
            value=np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32),
            expected=False,
            label="matrix_float32_all_finite_not_nan",
        ),
        TestCase(
            value=np.array([[np.nan, np.nan], [np.nan, np.nan]], dtype=np.float64),
            expected=True,
            label="matrix_float64_all_nan",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_isnan(self, test_case: TestCase) -> None:
        if expect_error(isnan, test_case.expected, test_case.value):
            return

        result = isnan(test_case.value)
        assert result == test_case.expected


class TestIsfinite(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[bool, Type[Exception]]
        value: Any

    test_cases = [
        TestCase(
            value=None,
            expected=False,
            label="none_not_finite",
        ),
        TestCase(
            value=float("nan"),
            expected=False,
            label="builtin_float_nan_not_finite",
        ),
        TestCase(
            value=float("inf"),
            expected=False,
            label="builtin_float_inf_not_finite",
        ),
        TestCase(
            value=float("-inf"),
            expected=False,
            label="builtin_float_neg_inf_not_finite",
        ),
        TestCase(
            value=0.0,
            expected=True,
            label="builtin_float_zero_finite",
        ),
        TestCase(
            value=1.5,
            expected=True,
            label="builtin_float_normal_finite",
        ),
        TestCase(
            value=-3.14,
            expected=True,
            label="builtin_float_negative_finite",
        ),
        TestCase(
            value=0,
            expected=True,
            label="builtin_int_zero_finite",
        ),
        TestCase(
            value=42,
            expected=True,
            label="builtin_int_positive_finite",
        ),
        TestCase(
            value=-17,
            expected=True,
            label="builtin_int_negative_finite",
        ),
        TestCase(
            value=True,
            expected=True,
            label="builtin_bool_true_finite",
        ),
        TestCase(
            value=False,
            expected=True,
            label="builtin_bool_false_finite",
        ),
        TestCase(
            value=np.nan,
            expected=False,
            label="numpy_nan_not_finite",
        ),
        TestCase(
            value=np.inf,
            expected=False,
            label="numpy_inf_not_finite",
        ),
        TestCase(
            value=-np.inf,
            expected=False,
            label="numpy_neg_inf_not_finite",
        ),
        TestCase(
            value=np.float32(np.nan),
            expected=False,
            label="numpy_float32_nan_not_finite",
        ),
        TestCase(
            value=np.float64(np.nan),
            expected=False,
            label="numpy_float64_nan_not_finite",
        ),
        TestCase(
            value=np.float32(np.inf),
            expected=False,
            label="numpy_float32_inf_not_finite",
        ),
        TestCase(
            value=np.float64(-np.inf),
            expected=False,
            label="numpy_float64_neg_inf_not_finite",
        ),
        TestCase(
            value=np.float32(3.14),
            expected=True,
            label="numpy_float32_normal_finite",
        ),
        TestCase(
            value=np.float64(2.718),
            expected=True,
            label="numpy_float64_normal_finite",
        ),
        TestCase(
            value=np.float32(0.0),
            expected=True,
            label="numpy_float32_zero_finite",
        ),
        TestCase(
            value=np.int32(100),
            expected=True,
            label="numpy_int32_finite",
        ),
        TestCase(
            value=np.int64(-256),
            expected=True,
            label="numpy_int64_finite",
        ),
        TestCase(
            value=np.int8(5),
            expected=True,
            label="numpy_int8_finite",
        ),
        TestCase(
            value=np.uint16(1000),
            expected=True,
            label="numpy_uint16_finite",
        ),
        TestCase(
            value=np.uint32(0),
            expected=True,
            label="numpy_uint32_zero_finite",
        ),
        TestCase(
            value=xp.nan,
            expected=False,
            label="xp_nan_not_finite",
        ),
        TestCase(
            value=xp.inf,
            expected=False,
            label="xp_inf_not_finite",
        ),
        TestCase(
            value=xp.float32(xp.inf),
            expected=False,
            label="xp_float32_inf_not_finite",
        ),
        TestCase(
            value=xp.float64(42.0),
            expected=True,
            label="xp_float64_normal_finite",
        ),
        TestCase(
            value=xp.int32(7),
            expected=True,
            label="xp_int32_finite",
        ),
        TestCase(
            value="42",
            expected=TypeError,
            label="string_raises_type_error",
        ),
        TestCase(
            value=[1, 2, 3],
            expected=TypeError,
            label="list_raises_type_error",
        ),
        TestCase(
            value={"key": "value"},
            expected=TypeError,
            label="dict_raises_type_error",
        ),
        TestCase(
            value=np.array([1.0, 2.0, 3.0], dtype=np.float32),
            expected=True,
            label="array_float32_all_finite",
        ),
        TestCase(
            value=np.array([1.0, np.nan, 3.0], dtype=np.float32),
            expected=False,
            label="array_float32_with_nan_not_all_finite",
        ),
        TestCase(
            value=np.array([np.nan, np.nan, np.nan], dtype=np.float32),
            expected=False,
            label="array_float32_all_nan_not_finite",
        ),
        TestCase(
            value=np.array([1.0, np.inf, -np.inf], dtype=np.float32),
            expected=False,
            label="array_float32_with_inf_not_all_finite",
        ),
        TestCase(
            value=np.array([np.inf, -np.inf, np.inf], dtype=np.float32),
            expected=False,
            label="array_float32_all_inf_not_finite",
        ),
        TestCase(
            value=np.array([np.nan, np.inf, -np.inf, 0.0], dtype=np.float32),
            expected=False,
            label="array_float32_mixed_not_all_finite",
        ),
        TestCase(
            value=np.array([0.0, 1.5, -2.3], dtype=np.float32),
            expected=True,
            label="array_float32_normal_values_all_finite",
        ),
        TestCase(
            value=np.array([1.0, 2.0, 3.0], dtype=np.float64),
            expected=True,
            label="array_float64_all_finite",
        ),
        TestCase(
            value=np.array([1.0, np.nan, 3.0], dtype=np.float64),
            expected=False,
            label="array_float64_with_nan_not_all_finite",
        ),
        TestCase(
            value=np.array([np.nan, np.nan], dtype=np.float64),
            expected=False,
            label="array_float64_all_nan_not_finite",
        ),
        TestCase(
            value=np.array([np.inf, -np.inf, 5.0], dtype=np.float64),
            expected=False,
            label="array_float64_with_inf_not_all_finite",
        ),
        TestCase(
            value=np.array([1.23, 4.56, 7.89], dtype=np.float64),
            expected=True,
            label="array_float64_normal_values_all_finite",
        ),
        TestCase(
            value=np.array([1, 2, 3], dtype=np.int32),
            expected=True,
            label="array_int32_all_finite",
        ),
        TestCase(
            value=np.array([0, -5, 100], dtype=np.int64),
            expected=True,
            label="array_int64_all_finite",
        ),
        TestCase(
            value=np.array([-128, 0, 127], dtype=np.int8),
            expected=True,
            label="array_int8_all_finite",
        ),
        TestCase(
            value=np.array([0, 100, 65535], dtype=np.uint16),
            expected=True,
            label="array_uint16_all_finite",
        ),
        TestCase(
            value=np.array([1000, 2000, 3000], dtype=np.uint32),
            expected=True,
            label="array_uint32_all_finite",
        ),
        TestCase(
            value=np.array([], dtype=np.float32),
            expected=True,
            label="array_empty_float32_all_finite",
        ),
        TestCase(
            value=np.array([], dtype=np.int64),
            expected=True,
            label="array_empty_int64_all_finite",
        ),
        TestCase(
            value=np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32),
            expected=True,
            label="matrix_float32_all_finite",
        ),
        TestCase(
            value=np.array([[1.0, np.nan], [np.inf, 4.0]], dtype=np.float64),
            expected=False,
            label="matrix_float64_with_nan_and_inf_not_all_finite",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_isfinite(self, test_case: TestCase) -> None:
        if expect_error(isfinite, test_case.expected, test_case.value):
            return

        result = isfinite(test_case.value)
        assert result == test_case.expected


class TestCastToFloat(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[Any, Type[Exception]]
        value: Any

    test_cases = [
        TestCase(
            value=True,
            expected=1.0,
            label="builtin_bool_true",
        ),
        TestCase(
            value=False,
            expected=0.0,
            label="builtin_bool_false",
        ),
        TestCase(
            value=42,
            expected=42.0,
            label="builtin_int_positive",
        ),
        TestCase(
            value=-17,
            expected=-17.0,
            label="builtin_int_negative",
        ),
        TestCase(
            value=0,
            expected=0.0,
            label="builtin_int_zero",
        ),
        TestCase(
            value=3.14,
            expected=3.14,
            label="builtin_float",
        ),
        TestCase(
            value=float("inf"),
            expected=float("inf"),
            label="builtin_float_inf",
        ),
        TestCase(
            value=float("-inf"),
            expected=float("-inf"),
            label="builtin_float_neg_inf",
        ),
        TestCase(
            value=np.int8(10),
            expected=np.float32(10.0),
            label="numpy_int8",
        ),
        TestCase(
            value=np.int16(100),
            expected=np.float32(100.0),
            label="numpy_int16",
        ),
        TestCase(
            value=np.int32(1000),
            expected=np.float32(1000.0),
            label="numpy_int32",
        ),
        TestCase(
            value=np.int64(10000),
            expected=np.float64(10000.0),
            label="numpy_int64",
        ),
        TestCase(
            value=np.uint8(255),
            expected=np.float32(255.0),
            label="numpy_uint8",
        ),
        TestCase(
            value=np.uint16(65535),
            expected=np.float32(65535.0),
            label="numpy_uint16",
        ),
        TestCase(
            value=np.uint32(4294967295),
            expected=np.float32(4294967295.0),
            label="numpy_uint32",
        ),
        TestCase(
            value=np.uint64(18446744073709551615),
            expected=np.float64(18446744073709551615.0),
            label="numpy_uint64",
        ),
        TestCase(
            value=np.float16(3.5),
            expected=np.float16(3.5),
            label="numpy_float16_unchanged",
        ),
        TestCase(
            value=np.float32(2.718),
            expected=np.float32(2.718),
            label="numpy_float32_unchanged",
        ),
        TestCase(
            value=np.float64(1.414),
            expected=np.float64(1.414),
            label="numpy_float64_unchanged",
        ),
        TestCase(
            value=np.array([1, 2, 3], dtype=np.int8),
            expected=np.array([1.0, 2.0, 3.0], dtype=np.float32),
            label="array_int8_to_float32",
        ),
        TestCase(
            value=np.array([10, 20, 30], dtype=np.int16),
            expected=np.array([10.0, 20.0, 30.0], dtype=np.float32),
            label="array_int16_to_float32",
        ),
        TestCase(
            value=np.array([100, 200, 300], dtype=np.int32),
            expected=np.array([100.0, 200.0, 300.0], dtype=np.float32),
            label="array_int32_to_float32",
        ),
        TestCase(
            value=np.array([1000, 2000, 3000], dtype=np.int64),
            expected=np.array([1000.0, 2000.0, 3000.0], dtype=np.float64),
            label="array_int64_to_float64",
        ),
        TestCase(
            value=np.array([1, 2, 3], dtype=np.uint8),
            expected=np.array([1.0, 2.0, 3.0], dtype=np.float32),
            label="array_uint8_to_float32",
        ),
        TestCase(
            value=np.array([100, 200, 300], dtype=np.uint16),
            expected=np.array([100.0, 200.0, 300.0], dtype=np.float32),
            label="array_uint16_to_float32",
        ),
        TestCase(
            value=np.array([1000, 2000, 3000], dtype=np.uint32),
            expected=np.array([1000.0, 2000.0, 3000.0], dtype=np.float32),
            label="array_uint32_to_float32",
        ),
        TestCase(
            value=np.array([10000, 20000, 30000], dtype=np.uint64),
            expected=np.array([10000.0, 20000.0, 30000.0], dtype=np.float64),
            label="array_uint64_to_float64",
        ),
        TestCase(
            value=np.array([1.5, 2.5, 3.5], dtype=np.float16),
            expected=np.array([1.5, 2.5, 3.5], dtype=np.float16),
            label="array_float16_unchanged",
        ),
        TestCase(
            value=np.array([1.1, 2.2, 3.3], dtype=np.float32),
            expected=np.array([1.1, 2.2, 3.3], dtype=np.float32),
            label="array_float32_unchanged",
        ),
        TestCase(
            value=np.array([1.23, 4.56, 7.89], dtype=np.float64),
            expected=np.array([1.23, 4.56, 7.89], dtype=np.float64),
            label="array_float64_unchanged",
        ),
        TestCase(
            value=xp.int8(5),
            expected=xp.float32(5.0),
            label="xp_int8",
        ),
        TestCase(
            value=xp.int16(50),
            expected=xp.float32(50.0),
            label="xp_int16",
        ),
        TestCase(
            value=xp.int32(500),
            expected=xp.float32(500.0),
            label="xp_int32",
        ),
        TestCase(
            value=xp.int64(5000),
            expected=xp.float64(5000.0),
            label="xp_int64",
        ),
        TestCase(
            value=xp.float32(2.5),
            expected=xp.float32(2.5),
            label="xp_float32_unchanged",
        ),
        TestCase(
            value=xp.float64(3.5),
            expected=xp.float64(3.5),
            label="xp_float64_unchanged",
        ),
        TestCase(
            value=xp.array([1, 2, 3], dtype=xp.int32),
            expected=xp.array([1.0, 2.0, 3.0], dtype=xp.float32),
            label="xp_array_int32_to_float32",
        ),
        TestCase(
            value=xp.array([10, 20, 30], dtype=xp.int64),
            expected=xp.array([10.0, 20.0, 30.0], dtype=xp.float64),
            label="xp_array_int64_to_float64",
        ),
        TestCase(
            value=xp.array([1.1, 2.2], dtype=xp.float32),
            expected=xp.array([1.1, 2.2], dtype=xp.float32),
            label="xp_array_float32_unchanged",
        ),
        TestCase(
            value=xp.array([1.23, 4.56], dtype=xp.float64),
            expected=xp.array([1.23, 4.56], dtype=xp.float64),
            label="xp_array_float64_unchanged",
        ),
        TestCase(
            value="42",
            expected=TypeError,
            label="string_raises_type_error",
        ),
        TestCase(
            value=[1, 2, 3],
            expected=TypeError,
            label="list_raises_type_error",
        ),
        TestCase(
            value=None,
            expected=TypeError,
            label="none_raises_type_error",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_cast_to_float(self, test_case: TestCase) -> None:
        if not expect_error(cast_to_float, test_case.expected, test_case.value):
            result = cast_to_float(test_case.value)
            assert_array_equal(result, test_case.expected)


class TestInferDtype(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[DTypeLike, Type[Exception]]
        value: Any
        dtype: Any

    test_cases = [
        TestCase(
            value=None,
            dtype=np.int32,
            expected=np.float32,
            label="none_returns_float32",
        ),
        TestCase(
            value=42,
            dtype=np.int32,
            expected=np.int32,
            label="builtin_int_with_int32_dtype",
        ),
        TestCase(
            value=3.14,
            dtype=np.float64,
            expected=np.float64,
            label="builtin_float_with_float64_dtype",
        ),
        TestCase(
            value=float("nan"),
            dtype=np.int32,
            expected=np.float32,
            label="builtin_nan_with_int_dtype_returns_float32",
        ),
        TestCase(
            value=float("nan"),
            dtype=np.float64,
            expected=np.float64,
            label="builtin_nan_with_float64_dtype_preserves",
        ),
        TestCase(
            value=float("inf"),
            dtype=np.int32,
            expected=np.float32,
            label="builtin_inf_with_int_dtype_returns_float32",
        ),
        TestCase(
            value=float("inf"),
            dtype=np.float32,
            expected=np.float32,
            label="builtin_inf_with_float32_dtype_preserves",
        ),
        TestCase(
            value=float("-inf"),
            dtype=np.int64,
            expected=np.float32,
            label="builtin_neg_inf_with_int_dtype_returns_float32",
        ),
        TestCase(
            value=True,
            dtype=np.bool_,
            expected=np.bool_,
            label="builtin_bool_with_bool_dtype",
        ),
        TestCase(
            value=False,
            dtype=np.int8,
            expected=np.int8,
            label="builtin_bool_false_with_int8_dtype",
        ),
        TestCase(
            value=np.int32(100),
            dtype=np.int32,
            expected=np.int32,
            label="numpy_int32_with_int32_dtype",
        ),
        TestCase(
            value=np.float64(2.718),
            dtype=np.float64,
            expected=np.float64,
            label="numpy_float64_with_float64_dtype",
        ),
        TestCase(
            value=np.nan,
            dtype=np.int32,
            expected=np.float32,
            label="numpy_nan_with_int_dtype_returns_float32",
        ),
        TestCase(
            value=np.nan,
            dtype=np.float64,
            expected=np.float64,
            label="numpy_nan_with_float64_dtype_preserves",
        ),
        TestCase(
            value=np.inf,
            dtype=np.int64,
            expected=np.float32,
            label="numpy_inf_with_int_dtype_returns_float32",
        ),
        TestCase(
            value=np.inf,
            dtype=np.float32,
            expected=np.float32,
            label="numpy_inf_with_float32_dtype_preserves",
        ),
        TestCase(
            value=np.float32(1.5),
            dtype=np.int16,
            expected=np.int16,
            label="numpy_float32_finite_with_int_dtype_preserves",
        ),
        TestCase(
            value=np.int8(7),
            dtype=np.float64,
            expected=np.float64,
            label="numpy_int8_with_float64_dtype",
        ),
        TestCase(
            value=np.uint32(500),
            dtype=np.uint32,
            expected=np.uint32,
            label="numpy_uint32_with_uint32_dtype",
        ),
        TestCase(
            value=xp.int32(42),
            dtype=xp.int32,
            expected=xp.int32,
            label="xp_int_with_int32_dtype",
        ),
        TestCase(
            value=xp.float64(3.14),
            dtype=xp.float64,
            expected=xp.float64,
            label="xp_float64_with_float64_dtype",
        ),
        TestCase(
            value=xp.nan,
            dtype=xp.int32,
            expected=xp.float32,
            label="xp_nan_with_int_dtype_returns_float32",
        ),
        TestCase(
            value=xp.inf,
            dtype=xp.float64,
            expected=xp.float64,
            label="xp_inf_with_float64_dtype_preserves",
        ),
        TestCase(
            value=xp.int64(-999),
            dtype=xp.int64,
            expected=xp.int64,
            label="xp_int64_with_int64_dtype",
        ),
        TestCase(
            value="42",
            dtype=np.int32,
            expected=TypeError,
            label="string_raises_type_error",
        ),
        TestCase(
            value=[1, 2, 3],
            dtype=np.int32,
            expected=TypeError,
            label="list_raises_type_error",
        ),
        TestCase(
            value={"key": 42},
            dtype=np.float32,
            expected=TypeError,
            label="dict_raises_type_error",
        ),
        TestCase(
            value=np.array(["hello", "world"], dtype=object),
            dtype=np.int32,
            expected=TypeError,
            label="numpy_string_object_array_raises_type_error",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_infer_dtype(self, test_case: TestCase) -> None:
        if expect_error(infer_dtype, test_case.expected, test_case.value, test_case.dtype):
            return

        result = infer_dtype(test_case.value, test_case.dtype)
        assert result == test_case.expected


class TestClamp(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[int, float, Type[Exception]]
        value: Any
        min_value: Any
        max_value: Any

    test_cases = [
        TestCase(
            value=5,
            min_value=0,
            max_value=10,
            expected=5,
            label="int_within_range",
        ),
        TestCase(
            value=-5,
            min_value=0,
            max_value=10,
            expected=0,
            label="int_below_min",
        ),
        TestCase(
            value=15,
            min_value=0,
            max_value=10,
            expected=10,
            label="int_above_max",
        ),
        TestCase(
            value=0,
            min_value=0,
            max_value=10,
            expected=0,
            label="int_equals_min",
        ),
        TestCase(
            value=10,
            min_value=0,
            max_value=10,
            expected=10,
            label="int_equals_max",
        ),
        TestCase(
            value=5.5,
            min_value=0.0,
            max_value=10.0,
            expected=5.5,
            label="float_within_range",
        ),
        TestCase(
            value=-2.5,
            min_value=0.0,
            max_value=10.0,
            expected=0.0,
            label="float_below_min",
        ),
        TestCase(
            value=12.7,
            min_value=0.0,
            max_value=10.0,
            expected=10.0,
            label="float_above_max",
        ),
        TestCase(
            value=0.0,
            min_value=0.0,
            max_value=10.0,
            expected=0.0,
            label="float_equals_min",
        ),
        TestCase(
            value=10.0,
            min_value=0.0,
            max_value=10.0,
            expected=10.0,
            label="float_equals_max",
        ),
        TestCase(
            value=-100,
            min_value=-50,
            max_value=-10,
            expected=-50,
            label="negative_range_below",
        ),
        TestCase(
            value=-30,
            min_value=-50,
            max_value=-10,
            expected=-30,
            label="negative_range_within",
        ),
        TestCase(
            value=0,
            min_value=-50,
            max_value=-10,
            expected=-10,
            label="negative_range_above",
        ),
        TestCase(
            value=np.int32(5),
            min_value=np.int32(0),
            max_value=np.int32(10),
            expected=5,
            label="numpy_int32_all",
        ),
        TestCase(
            value=np.int64(5),
            min_value=np.int64(0),
            max_value=np.int64(10),
            expected=5,
            label="numpy_int64_all",
        ),
        TestCase(
            value=np.float32(5.5),
            min_value=np.float32(0.0),
            max_value=np.float32(10.0),
            expected=5.5,
            label="numpy_float32_all",
        ),
        TestCase(
            value=np.float64(5.5),
            min_value=np.float64(0.0),
            max_value=np.float64(10.0),
            expected=5.5,
            label="numpy_float64_all",
        ),
        TestCase(
            value=np.int64(5),
            min_value=0,
            max_value=10,
            expected=5,
            label="numpy_int_with_python_int_bounds",
        ),
        TestCase(
            value=5,
            min_value=np.int32(0),
            max_value=np.int64(10),
            expected=5,
            label="python_int_with_numpy_int_bounds",
        ),
        TestCase(
            value=5,
            min_value=0.0,
            max_value=10.0,
            expected=5.0,
            label="int_value_with_float_bounds_promotes_to_float",
        ),
        TestCase(
            value=5.0,
            min_value=0,
            max_value=10,
            expected=5.0,
            label="float_value_with_int_bounds_stays_float",
        ),
        TestCase(
            value=5,
            min_value=0.5,
            max_value=10,
            expected=5.0,
            label="mixed_types_int_value_float_min",
        ),
        TestCase(
            value=5,
            min_value=0,
            max_value=10.5,
            expected=5.0,
            label="mixed_types_int_value_float_max",
        ),
        TestCase(
            value=np.int32(5),
            min_value=0.0,
            max_value=10.0,
            expected=5.0,
            label="numpy_int_with_float_bounds",
        ),
        TestCase(
            value=np.float32(5.5),
            min_value=0,
            max_value=10,
            expected=5.5,
            label="numpy_float_with_int_bounds",
        ),
        TestCase(
            value=5,
            min_value=7,
            max_value=7,
            expected=7,
            label="strict_bounds_int_equal",
        ),
        TestCase(
            value=12.0,
            min_value=7.0,
            max_value=7.0,
            expected=7.0,
            label="strict_bounds_float_equal",
        ),
        TestCase(
            value=5,
            min_value=0,
            max_value=0,
            expected=0,
            label="strict_bounds_zero_int",
        ),
        TestCase(
            value=5.0,
            min_value=0.0,
            max_value=0.0,
            expected=0.0,
            label="strict_bounds_zero_float",
        ),
        TestCase(
            value=5,
            min_value=0,
            max_value=0.0,
            expected=0.0,
            label="strict_bounds_zero_mixed_int_float",
        ),
        TestCase(
            value=5.0,
            min_value=0,
            max_value=0.0,
            expected=0.0,
            label="strict_bounds_zero_mixed_float",
        ),
        TestCase(
            value=5,
            min_value=10,
            max_value=0,
            expected=0,
            label="inverted_bounds_max_takes_precedence",
        ),
        TestCase(
            value=15,
            min_value=20,
            max_value=10,
            expected=10,
            label="inverted_bounds_value_between",
        ),
        TestCase(
            value=25,
            min_value=20,
            max_value=10,
            expected=10,
            label="inverted_bounds_value_above_both",
        ),
        TestCase(
            value=5,
            min_value=None,
            max_value=10,
            expected=5,
            label="none_min_within_max",
        ),
        TestCase(
            value=5,
            min_value=None,
            max_value=3,
            expected=3,
            label="none_min_above_max",
        ),
        TestCase(
            value=5,
            min_value=7,
            max_value=None,
            expected=7,
            label="none_max_below_min",
        ),
        TestCase(
            value=5,
            min_value=3,
            max_value=None,
            expected=5,
            label="none_max_above_min",
        ),
        TestCase(
            value=5,
            min_value=None,
            max_value=None,
            expected=5,
            label="both_bounds_none",
        ),
        TestCase(
            value=5.5,
            min_value=None,
            max_value=None,
            expected=5.5,
            label="both_bounds_none_float",
        ),
        TestCase(
            value=float("inf"),
            min_value=0.0,
            max_value=100.0,
            expected=100.0,
            label="positive_infinity_clamped_to_max",
        ),
        TestCase(
            value=float("-inf"),
            min_value=0.0,
            max_value=100.0,
            expected=0.0,
            label="negative_infinity_clamped_to_min",
        ),
        TestCase(
            value=5.0,
            min_value=float("-inf"),
            max_value=100.0,
            expected=5.0,
            label="neg_inf_min_bound",
        ),
        TestCase(
            value=5.0,
            min_value=0.0,
            max_value=float("inf"),
            expected=5.0,
            label="pos_inf_max_bound",
        ),
        TestCase(
            value=float("inf"),
            min_value=float("-inf"),
            max_value=float("inf"),
            expected=float("inf"),
            label="inf_value_inf_bounds",
        ),
        TestCase(
            value=1.0,
            min_value=0.0,
            max_value=float("-inf"),
            expected=float("-inf"),
            label="max_precedence_with_neg_inf",
        ),
        TestCase(
            value=float("nan"),
            min_value=0.0,
            max_value=10.0,
            expected=float("nan"),
            label="nan_value_with_bounds",
        ),
        TestCase(
            value=5.0,
            min_value=float("nan"),
            max_value=10.0,
            expected=5.0,
            label="nan_min_bound",
        ),
        TestCase(
            value=5.0,
            min_value=7.0,
            max_value=float("nan"),
            expected=7.0,
            label="nan_max_bound",
        ),
        TestCase(
            value=np.nan,
            min_value=0.0,
            max_value=10.0,
            expected=float("nan"),
            label="numpy_nan_value",
        ),
        TestCase(
            value="5",
            min_value=0,
            max_value=10,
            expected=TypeError,
            label="string_value",
        ),
        TestCase(
            value=5,
            min_value="0",
            max_value=10,
            expected=TypeError,
            label="string_min_bound",
        ),
        TestCase(
            value=5,
            min_value=0,
            max_value="10",
            expected=TypeError,
            label="string_max_bound",
        ),
        TestCase(
            value=[5],
            min_value=0,
            max_value=10,
            expected=TypeError,
            label="list_value",
        ),
        TestCase(
            value=None,
            min_value=0,
            max_value=10,
            expected=TypeError,
            label="none_value",
        ),
        TestCase(
            value=5,
            min_value=[0],
            max_value=10,
            expected=TypeError,
            label="list_min_bound",
        ),
        TestCase(
            value=5,
            min_value=0,
            max_value={"max": 10},
            expected=TypeError,
            label="dict_max_bound",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_clamp(self, test_case: TestCase) -> None:
        if expect_error(
            clamp,
            test_case.expected,
            test_case.value,
            test_case.min_value,
            test_case.max_value,
        ):
            return

        result = clamp(test_case.value, test_case.min_value, test_case.max_value)
        assert_array_equal(result, test_case.expected)


class TestPad(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[np.ndarray, Type[Exception]]
        array: Any
        left: Any
        right: Any
        value: Any

    test_cases = [
        TestCase(
            array=np.array([], dtype=np.int64),
            left=0,
            right=0,
            value=0,
            expected=np.array([], dtype=np.int64),
            label="empty_int_array_empty_padding",
        ),
        TestCase(
            array=np.array([], dtype=np.float32),
            left=0,
            right=0,
            value=0,
            expected=np.array([], dtype=np.float32),
            label="empty_float_array_empty_padding",
        ),
        TestCase(
            array=np.array([-1], dtype=np.int64),
            left=0,
            right=0,
            value=0,
            expected=np.array([], dtype=np.int64),
            label="nonempty_array_empty_padding",
        ),
        TestCase(
            array=np.array([1, 2, 3, 4, 5], dtype=np.int64),
            left=0,
            right=5,
            value=0,
            expected=np.array([1, 2, 3, 4, 5], dtype=np.int64),
            label="no_padding",
        ),
        TestCase(
            array=np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64),
            left=-2,
            right=5,
            value=0,
            expected=np.array([0.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64),
            label="left_padding_only",
        ),
        TestCase(
            array=np.array([1, 2, 3, 4, 5]),
            left=0,
            right=7,
            value=0,
            expected=np.array([1, 2, 3, 4, 5, 0, 0]),
            label="right_padding_only",
        ),
        TestCase(
            array=np.array([1, 2, 3, 4, 5]),
            left=-2,
            right=7,
            value=0,
            expected=np.array([0, 0, 1, 2, 3, 4, 5, 0, 0]),
            label="both_sides_padding",
        ),
        TestCase(
            array=np.array([1, 2, 3, 4, 5]),
            left=1,
            right=4,
            value=0,
            expected=np.array([2, 3, 4]),
            label="slice_middle",
        ),
        TestCase(
            array=np.array([1, 2, 3, 4, 5]),
            left=3,
            right=8,
            value=0,
            expected=np.array([4, 5, 0, 0, 0]),
            label="slice_end_with_padding",
        ),
        TestCase(
            array=np.array([1, 2, 3, 4, 5]),
            left=-5,
            right=-2,
            value=9,
            expected=np.array([9, 9, 9]),
            label="negative_indices_with_custom_value",
        ),
        TestCase(
            array=np.array([1, 2, 3, 4, 5]),
            left=10,
            right=15,
            value=7,
            expected=np.array([7, 7, 7, 7, 7]),
            label="completely_outside_right",
        ),
        TestCase(
            array=np.array([1, 2, 3], dtype=np.int64),
            left=-1,
            right=4,
            value=np.nan,
            expected=np.array([np.nan, 1.0, 2.0, 3.0, np.nan], dtype=np.float32),
            label="float_array_with_nan_padding_changes_dtype",
        ),
        TestCase(
            array=np.array([[1.5, 2.5, 3.5]]),
            left=-1,
            right=4,
            value=np.nan,
            expected=ValueError,
            label="array_not_1d",
        ),
        TestCase(
            array=[1, 2, 3],
            left=1,
            right=2,
            value=0,
            expected=TypeError,
            label="list_not_array",
        ),
        TestCase(
            array=np.array([1, 2, 3], dtype=np.int16),
            left=1,
            right=2,
            value=0,
            expected=np.array([2], dtype=np.int16),
            label="preservers_dtype_int16",
        ),
        TestCase(
            array=np.array([1, 2, 3], dtype=np.int64),
            left=None,
            right=2,
            value=0,
            expected=TypeError,
            label="invalid_left_padding_none",
        ),
        TestCase(
            array=np.array([1, 2, 3], dtype=np.int64),
            left=1,
            right=None,
            value=0,
            expected=TypeError,
            label="invalid_right_padding_none",
        ),
        TestCase(
            array=np.array([1, 2, 3], dtype=np.int64),
            left=1.0,
            right=2,
            value=0,
            expected=TypeError,
            label="invalid_left_padding_float",
        ),
        TestCase(
            array=np.array([1, 2, 3], dtype=np.int64),
            left=3,
            right=2,
            value=0,
            expected=ValueError,
            label="out_of_order_padding",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_pad(self, test_case: TestCase) -> None:
        if expect_error(
            pad,
            test_case.expected,
            test_case.array,
            test_case.left,
            test_case.right,
            test_case.value,
        ):
            return

        result = pad(test_case.array, test_case.left, test_case.right, test_case.value)
        assert_array_equal(result, test_case.expected)


class TestTrim(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[np.ndarray, Type[Exception]]
        input_array: Any

    test_cases = [
        TestCase(
            input_array=np.array([1, 1, 2, 2, 3, 3, 3, 3]),
            expected=np.array([1, 1, 2, 2, 3]),
            label="trailing_duplicates",
        ),
        TestCase(
            input_array=np.array([5, 5, 5, 5]),
            expected=np.array([5]),
            label="all_same_values",
        ),
        TestCase(
            input_array=np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
            expected=np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
            label="no_duplicates",
        ),
        TestCase(
            input_array=np.array([1, 1, 1, 2, 3, 3]),
            expected=np.array([1, 1, 1, 2, 3]),
            label="duplicates_at_start_and_end",
        ),
        TestCase(
            input_array=np.array([1, 2, 1, 2, 1, 1]),
            expected=np.array([1, 2, 1, 2, 1]),
            label="alternating_with_trailing_dup",
        ),
        TestCase(
            input_array=np.array([7]),
            expected=np.array([7]),
            label="single_element",
        ),
        TestCase(
            input_array=np.array([1, 2, 2, 2, 2, 2]),
            expected=np.array([1, 2]),
            label="many_trailing_duplicates",
        ),
        TestCase(
            input_array=np.array([0, 0, 1, 1, 0, 0, 0]),
            expected=np.array([0, 0, 1, 1, 0]),
            label="zero_values_with_trailing_dups",
        ),
        TestCase(
            input_array=np.array([[1, 2]]),
            expected=ValueError,
            label="not_1d_array",
        ),
        TestCase(
            input_array=[1, 2],
            expected=TypeError,
            label="not_an_array",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_trim(self, test_case: TestCase) -> None:
        if expect_error(trim, test_case.expected, test_case.input_array):
            return

        result = trim(test_case.input_array)
        assert_array_equal(result, test_case.expected)


class TestIsIncreasing(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: bool
        input_array: Any

    test_cases = [
        TestCase(
            input_array=np.array([], dtype=np.int32),
            expected=True,
            label="empty_array_int32",
        ),
        TestCase(
            input_array=np.array([], dtype=np.float64),
            expected=True,
            label="empty_array_float64",
        ),
        TestCase(
            input_array=np.array([5], dtype=np.int64),
            expected=True,
            label="singleton_int64",
        ),
        TestCase(
            input_array=np.array([3.14], dtype=np.float32),
            expected=True,
            label="singleton_float32",
        ),
        TestCase(
            input_array=np.array([1, 2, 5, 10], dtype=np.int32),
            expected=True,
            label="strictly_increasing_int32",
        ),
        TestCase(
            input_array=np.array([1.0, 2.5, 3.7, 10.2], dtype=np.float64),
            expected=True,
            label="strictly_increasing_float64",
        ),
        TestCase(
            input_array=np.array([-5, -2, 0, 3, 7], dtype=np.int64),
            expected=True,
            label="strictly_increasing_negative_to_positive_int64",
        ),
        TestCase(
            input_array=np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32),
            expected=True,
            label="strictly_increasing_small_floats",
        ),
        TestCase(
            input_array=np.array([5, 5, 5, 5], dtype=np.int32),
            expected=False,
            label="constant_sequence_int32",
        ),
        TestCase(
            input_array=np.array([2.0, 2.0, 2.0], dtype=np.float64),
            expected=False,
            label="constant_sequence_float64",
        ),
        TestCase(
            input_array=np.array([1, 2, 2, 5], dtype=np.int64),
            expected=False,
            label="weakly_increasing_int64",
        ),
        TestCase(
            input_array=np.array([1.0, 2.0, 2.0, 3.0], dtype=np.float32),
            expected=False,
            label="weakly_increasing_float32",
        ),
        TestCase(
            input_array=np.array([1, 3, 2, 4], dtype=np.int32),
            expected=False,
            label="non_monotonic_int32",
        ),
        TestCase(
            input_array=np.array([5.0, 10.0, 3.0, 15.0], dtype=np.float64),
            expected=False,
            label="non_monotonic_float64",
        ),
        TestCase(
            input_array=np.array([10, 5, 2, 1], dtype=np.int64),
            expected=False,
            label="strictly_decreasing_int64",
        ),
        TestCase(
            input_array=np.array([10.0, 5.0, 2.0, 1.0], dtype=np.float32),
            expected=False,
            label="strictly_decreasing_float32",
        ),
        TestCase(
            input_array=np.array([0, -1, -2, -3], dtype=np.int32),
            expected=False,
            label="strictly_decreasing_to_negative_int32",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_is_increasing(self, test_case: TestCase) -> None:
        result = is_increasing(test_case.input_array)
        assert result == test_case.expected
