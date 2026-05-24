from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import numpy as np
import pytest

from sampletones_core.array import xp
from sampletones_shared.utils.transformations.functions import energy, exp, identity, power, power_inverse
from tests.sampletones.arrays import assert_array_equal
from tests.sampletones.errors import expect_error, expect_warning
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


class TestIdentity(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Any
        value: Any

    test_cases = [
        TestCase(
            value=True,
            expected=True,
            label="bool_true",
        ),
        TestCase(
            value=False,
            expected=False,
            label="bool_false",
        ),
        TestCase(
            value=0,
            expected=0,
            label="int_zero",
        ),
        TestCase(
            value=42,
            expected=42,
            label="int_positive",
        ),
        TestCase(
            value=-17,
            expected=-17,
            label="int_negative",
        ),
        TestCase(
            value=0.0,
            expected=0.0,
            label="float_zero",
        ),
        TestCase(
            value=3.14,
            expected=3.14,
            label="float_positive",
        ),
        TestCase(
            value=-2.718,
            expected=-2.718,
            label="float_negative",
        ),
        TestCase(
            value=np.int32(100),
            expected=np.int32(100),
            label="numpy_int32",
        ),
        TestCase(
            value=np.int64(-256),
            expected=np.int64(-256),
            label="numpy_int64",
        ),
        TestCase(
            value=np.float32(1.5),
            expected=np.float32(1.5),
            label="numpy_float32",
        ),
        TestCase(
            value=np.float64(2.5),
            expected=np.float64(2.5),
            label="numpy_float64",
        ),
        TestCase(
            value=xp.int32(7),
            expected=xp.int32(7),
            label="xp_int32",
        ),
        TestCase(
            value=xp.int64(-999),
            expected=xp.int64(-999),
            label="xp_int64",
        ),
        TestCase(
            value=xp.float32(3.14),
            expected=xp.float32(3.14),
            label="xp_float32",
        ),
        TestCase(
            value=xp.float64(-1.23),
            expected=xp.float64(-1.23),
            label="xp_float64",
        ),
        TestCase(
            value=np.array([1, 2, 3]),
            expected=np.array([1, 2, 3]),
            label="numpy_array_int",
        ),
        TestCase(
            value=np.array([1.5, 2.5, 3.5], dtype=np.float32),
            expected=np.array([1.5, 2.5, 3.5], dtype=np.float32),
            label="numpy_array_float32",
        ),
        TestCase(
            value=xp.array([4, 5, 6]),
            expected=xp.array([4, 5, 6]),
            label="xp_array_int",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_identity(self, test_case: TestCase) -> None:
        result = identity(test_case.value)
        assert_array_equal(result, test_case.expected)


class TestEnergy(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Any
        value: Any

    test_cases = [
        TestCase(
            value=True,
            expected=np.int8(1),
            label="bool_true",
        ),
        TestCase(
            value=False,
            expected=np.int8(0),
            label="bool_false",
        ),
        TestCase(
            value=0,
            expected=np.int64(0),
            label="int_zero",
        ),
        TestCase(
            value=3,
            expected=np.int64(9),
            label="int_positive",
        ),
        TestCase(
            value=-4,
            expected=np.int64(16),
            label="int_negative",
        ),
        TestCase(
            value=0.0,
            expected=np.float64(0.0),
            label="float_zero",
        ),
        TestCase(
            value=2.0,
            expected=np.float64(4.0),
            label="float_positive",
        ),
        TestCase(
            value=-3.0,
            expected=np.float64(9.0),
            label="float_negative",
        ),
        TestCase(
            value=0.5,
            expected=np.float64(0.25),
            label="float_fractional",
        ),
        TestCase(
            value=np.int32(5),
            expected=np.int32(25),
            label="numpy_int32",
        ),
        TestCase(
            value=np.int64(-10),
            expected=np.int64(100),
            label="numpy_int64",
        ),
        TestCase(
            value=np.float32(2.5),
            expected=np.float32(6.25),
            label="numpy_float32",
        ),
        TestCase(
            value=np.float64(-1.5),
            expected=np.float64(2.25),
            label="numpy_float64",
        ),
        TestCase(
            value=xp.int32(6),
            expected=xp.int32(36),
            label="xp_int32",
        ),
        TestCase(
            value=xp.int64(-8),
            expected=xp.int64(64),
            label="xp_int64",
        ),
        TestCase(
            value=xp.float32(1.5),
            expected=xp.float32(2.25),
            label="xp_float32",
        ),
        TestCase(
            value=xp.float64(-2.5),
            expected=xp.float64(6.25),
            label="xp_float64",
        ),
        TestCase(
            value=np.array([2.5, 3.2, 4.1]),
            expected=np.array([6.25, 10.24, 16.81]),
            label="numpy_array_float",
        ),
        TestCase(
            value=np.array([1.0, 2.0, 3.0], dtype=np.float32),
            expected=np.array([1.0, 4.0, 9.0], dtype=np.float32),
            label="numpy_array_float32",
        ),
        TestCase(
            value=xp.array([-2.5, -3.0, -4.2]),
            expected=xp.array([6.25, 9.0, 17.64]),
            label="xp_array_float",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_energy(self, test_case: TestCase) -> None:
        result = energy(test_case.value)
        assert_array_equal(result, test_case.expected)


class TestExp(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Any
        value: Any

    test_cases = [
        TestCase(
            value=True,
            expected=np.float16(np.e),
            label="bool_true",
        ),
        TestCase(
            value=False,
            expected=np.float16(1.0),
            label="bool_false",
        ),
        TestCase(
            value=0,
            expected=np.float64(1.0),
            label="int_zero",
        ),
        TestCase(
            value=1,
            expected=np.float64(np.e),
            label="int_one",
        ),
        TestCase(
            value=2,
            expected=np.float64(np.e**2),
            label="int_two",
        ),
        TestCase(
            value=-1,
            expected=np.float64(1.0 / np.e),
            label="int_negative_one",
        ),
        TestCase(
            value=0.0,
            expected=np.float64(1.0),
            label="float_zero",
        ),
        TestCase(
            value=1.0,
            expected=np.float64(np.e),
            label="float_one",
        ),
        TestCase(
            value=-1.0,
            expected=np.float64(1.0 / np.e),
            label="float_negative_one",
        ),
        TestCase(
            value=0.5,
            expected=np.float64(np.e**0.5),
            label="float_half",
        ),
        TestCase(
            value=np.int32(0),
            expected=np.float64(1.0),
            label="numpy_int32_zero",
        ),
        TestCase(
            value=np.int64(2),
            expected=np.float64(np.e**2),
            label="numpy_int64",
        ),
        TestCase(
            value=np.float32(1.0),
            expected=np.float32(np.e),
            label="numpy_float32",
        ),
        TestCase(
            value=np.float64(-0.5),
            expected=np.float64(np.e**-0.5),
            label="numpy_float64",
        ),
        TestCase(
            value=xp.int32(1),
            expected=np.float64(np.e),
            label="xp_int32",
        ),
        TestCase(
            value=xp.int64(-1),
            expected=np.float64(1.0 / np.e),
            label="xp_int64",
        ),
        TestCase(
            value=xp.float32(2.0),
            expected=xp.float32(np.e**2),
            label="xp_float32",
        ),
        TestCase(
            value=xp.float64(0.5),
            expected=xp.float64(np.e**0.5),
            label="xp_float64",
        ),
        TestCase(
            value=np.array([0.5, 1.2, 2.3]),
            expected=np.array([np.e**0.5, np.e**1.2, np.e**2.3]),
            label="numpy_array_float",
        ),
        TestCase(
            value=np.array([0.0, 1.0, -1.0], dtype=np.float32),
            expected=np.array([1.0, np.e, 1.0 / np.e], dtype=np.float32),
            label="numpy_array_float32",
        ),
        TestCase(
            value=xp.array([1.5, 2.7, 3.1]),
            expected=xp.array([np.e**1.5, np.e**2.7, np.e**3.1]),
            label="xp_array_float",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_exp(self, test_case: TestCase) -> None:
        result = exp(test_case.value)
        assert_array_equal(result, test_case.expected)


class TestPower(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Any
        value: Any
        a: float
        expected_warning: Any = None

    test_cases = [
        TestCase(
            value=True,
            a=2.0,
            expected=np.float64(1.0),
            label="bool_true",
        ),
        TestCase(
            value=False,
            a=2.0,
            expected=np.float64(0.0),
            label="bool_false",
        ),
        TestCase(
            value=2,
            a=0.0,
            expected=np.float64(1.0),
            label="int_power_zero",
        ),
        TestCase(
            value=0,
            a=2.0,
            expected=np.float64(0.0),
            label="int_zero_base",
        ),
        TestCase(
            value=0,
            a=0.0,
            expected=np.float64(1.0),
            label="int_zero_base_zero_power",
        ),
        TestCase(
            value=2,
            a=3.0,
            expected=np.float64(8.0),
            label="int_positive",
        ),
        TestCase(
            value=2,
            a=-2.0,
            expected=np.float64(0.25),
            label="int_negative_exponent",
        ),
        TestCase(
            value=-2,
            a=2.0,
            expected=np.float64(4.0),
            label="int_negative_base_even_power",
        ),
        TestCase(
            value=-2,
            a=3.0,
            expected=np.float64(-8.0),
            label="int_negative_base_odd_power",
        ),
        TestCase(
            value=4.0,
            a=0.5,
            expected=np.float64(2.0),
            label="float_square_root",
        ),
        TestCase(
            value=2.0,
            a=0.0,
            expected=np.float64(1.0),
            label="float_power_zero",
        ),
        TestCase(
            value=0.0,
            a=2.0,
            expected=np.float64(0.0),
            label="float_zero_base",
        ),
        TestCase(
            value=0.0,
            a=0.0,
            expected=np.float64(1.0),
            label="float_zero_base_zero_power",
        ),
        TestCase(
            value=3.0,
            a=2.0,
            expected=np.float64(9.0),
            label="float_positive",
        ),
        TestCase(
            value=2.0,
            a=-1.0,
            expected=np.float64(0.5),
            label="float_negative_exponent",
        ),
        TestCase(
            value=np.int32(3),
            a=2.0,
            expected=np.float64(9.0),
            label="numpy_int32",
        ),
        TestCase(
            value=np.int64(2),
            a=3.0,
            expected=np.float64(8.0),
            label="numpy_int64",
        ),
        TestCase(
            value=np.float32(2.0),
            a=3.0,
            expected=np.float32(8.0),
            label="numpy_float32",
        ),
        TestCase(
            value=np.float64(4.0),
            a=0.5,
            expected=np.float64(2.0),
            label="numpy_float64",
        ),
        TestCase(
            value=xp.int32(5),
            a=2.0,
            expected=np.float64(25.0),
            label="xp_int32",
        ),
        TestCase(
            value=xp.int64(3),
            a=3.0,
            expected=np.float64(27.0),
            label="xp_int64",
        ),
        TestCase(
            value=xp.float32(2.0),
            a=4.0,
            expected=xp.float32(16.0),
            label="xp_float32",
        ),
        TestCase(
            value=xp.float64(9.0),
            a=0.5,
            expected=xp.float64(3.0),
            label="xp_float64",
        ),
        TestCase(
            value=2.0,
            a=2.5,
            expected=np.float64(2.0**2.5),
            label="float_non_integer_exponent",
        ),
        TestCase(
            value=8,
            a=1.333333333,
            expected=np.float64(8**1.333333333),
            label="int_fractional_exponent",
        ),
        TestCase(
            value=3.5,
            a=-1.7,
            expected=np.float64(3.5**-1.7),
            label="float_negative_fractional_exponent",
        ),
        TestCase(
            value=0.5,
            a=2.3,
            expected=np.float64(0.5**2.3),
            label="fractional_base_non_integer_exponent",
        ),
        TestCase(
            value=-2.0,
            a=2.5,
            expected=np.float64(float("nan")),
            label="negative_base_non_integer_exponent_nan",
            expected_warning=RuntimeWarning,
        ),
        TestCase(
            value=np.float32(4.0),
            a=1.5,
            expected=np.float32(8.0),
            label="numpy_float32_non_integer_exponent",
        ),
        TestCase(
            value=-1,
            a=-1.0,
            expected=np.float64(-1.0),
            label="negative_one_to_negative_one",
        ),
        TestCase(
            value=-3,
            a=-2.0,
            expected=np.float64(1.0 / 9.0),
            label="negative_int_negative_even_power",
        ),
        TestCase(
            value=-3,
            a=-3.0,
            expected=np.float64(-1.0 / 27.0),
            label="negative_int_negative_odd_power",
        ),
        TestCase(
            value=np.array([2, 3, 4]),
            a=2.0,
            expected=np.array([4.0, 9.0, 16.0]),
            label="numpy_array_int",
        ),
        TestCase(
            value=np.array([1.0, 2.0, 3.0], dtype=np.float32),
            a=3.0,
            expected=np.array([1.0, 8.0, 27.0], dtype=np.float32),
            label="numpy_array_float32_integer_power",
        ),
        TestCase(
            value=np.array([2.5, 3.0, 4.2]),
            a=1.8,
            expected=np.array([2.5**1.8, 3.0**1.8, 4.2**1.8]),
            label="numpy_array_float",
        ),
        TestCase(
            value=np.array([1.5, 2.0, 3.5], dtype=np.float32),
            a=2.3,
            expected=np.array([1.5**2.3, 2.0**2.3, 3.5**2.3], dtype=np.float32),
            label="numpy_array_float32",
        ),
        TestCase(
            value=xp.array([2.2, 4.5, 8.1]),
            a=0.7,
            expected=xp.array([2.2**0.7, 4.5**0.7, 8.1**0.7]),
            label="xp_array_float",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_power(self, test_case: TestCase) -> None:
        result = expect_warning(power, test_case.expected_warning, test_case.value, test_case.a)
        assert_array_equal(result, test_case.expected)


class TestPowerInverse(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Any
        value: Any
        a: float
        expected_warning: Optional[Any] = None

    test_cases = [
        TestCase(
            value=True,
            a=2.0,
            expected=np.float64(1.0),
            label="bool_true",
        ),
        TestCase(
            value=False,
            a=2.0,
            expected=np.float64(0.0),
            label="bool_false",
        ),
        TestCase(
            value=2,
            a=0.0,
            expected=ZeroDivisionError,
            label="int_power_inverse_zero_inf",
        ),
        TestCase(
            value=0,
            a=0.0,
            expected=ZeroDivisionError,
            label="zero_base_power_inverse_zero_nan",
        ),
        TestCase(
            value=8,
            a=3.0,
            expected=np.float64(2.0),
            label="int_cube_root",
        ),
        TestCase(
            value=0,
            a=2.0,
            expected=np.float64(0.0),
            label="int_zero_base",
        ),
        TestCase(
            value=16,
            a=2.0,
            expected=np.float64(4.0),
            label="int_square_root",
        ),
        TestCase(
            value=4,
            a=-2.0,
            expected=np.float64(0.5),
            label="int_negative_exponent",
        ),
        TestCase(
            value=4.0,
            a=2.0,
            expected=np.float64(2.0),
            label="float_square_root",
        ),
        TestCase(
            value=0.0,
            a=2.0,
            expected=np.float64(0.0),
            label="float_zero_base",
        ),
        TestCase(
            value=27.0,
            a=3.0,
            expected=np.float64(3.0),
            label="float_cube_root",
        ),
        TestCase(
            value=2.0,
            a=-1.0,
            expected=np.float64(0.5),
            label="float_negative_exponent",
        ),
        TestCase(
            value=np.int32(16),
            a=2.0,
            expected=np.float64(4.0),
            label="numpy_int32",
        ),
        TestCase(
            value=np.int64(8),
            a=3.0,
            expected=np.float64(2.0),
            label="numpy_int64",
        ),
        TestCase(
            value=np.float32(9.0),
            a=2.0,
            expected=np.float32(3.0),
            label="numpy_float32",
        ),
        TestCase(
            value=np.float64(16.0),
            a=4.0,
            expected=np.float64(2.0),
            label="numpy_float64",
        ),
        TestCase(
            value=xp.int32(25),
            a=2.0,
            expected=np.float64(5.0),
            label="xp_int32",
        ),
        TestCase(
            value=xp.int64(27),
            a=3.0,
            expected=np.float64(3.0),
            label="xp_int64",
        ),
        TestCase(
            value=xp.float32(16.0),
            a=2.0,
            expected=xp.float32(4.0),
            label="xp_float32",
        ),
        TestCase(
            value=xp.float64(8.0),
            a=3.0,
            expected=xp.float64(2.0),
            label="xp_float64",
        ),
        TestCase(
            value=32.0,
            a=2.5,
            expected=np.float64(32.0 ** (1 / 2.5)),
            label="float_non_integer_exponent",
        ),
        TestCase(
            value=100,
            a=1.5,
            expected=np.float64(100 ** (1 / 1.5)),
            label="int_fractional_exponent",
        ),
        TestCase(
            value=5.0,
            a=-1.3,
            expected=np.float64(5.0 ** (1 / -1.3)),
            label="float_negative_fractional_exponent",
        ),
        TestCase(
            value=0.25,
            a=1.8,
            expected=np.float64(0.25 ** (1 / 1.8)),
            label="fractional_base_non_integer_exponent",
        ),
        TestCase(
            value=np.float32(16.0),
            a=2.4,
            expected=np.float32(16.0 ** (1 / 2.4)),
            label="numpy_float32_non_integer_exponent",
        ),
        TestCase(
            value=-1,
            a=-1.0,
            expected=np.float64(-1.0),
            label="negative_one_exponent_negative_one",
        ),
        TestCase(
            value=-8,
            a=3.0,
            expected=np.float64(np.nan),
            label="negative_int_odd_exponent",
            expected_warning=RuntimeWarning,
        ),
        TestCase(
            value=np.array([4, 9, 16]),
            a=2.0,
            expected=np.array([2.0, 3.0, 4.0]),
            label="numpy_array_int",
        ),
        TestCase(
            value=np.array([8.0, 27.0, 64.0], dtype=np.float32),
            a=3.0,
            expected=np.array([2.0, 3.0, 4.0], dtype=np.float32),
            label="numpy_array_float32_integer_exponent",
        ),
        TestCase(
            value=np.array([6.25, 10.24, 16.81]),
            a=1.7,
            expected=np.array([6.25 ** (1 / 1.7), 10.24 ** (1 / 1.7), 16.81 ** (1 / 1.7)]),
            label="numpy_array_float",
        ),
        TestCase(
            value=np.array([8.0, 27.0, 64.0], dtype=np.float32),
            a=2.5,
            expected=np.array([8.0 ** (1 / 2.5), 27.0 ** (1 / 2.5), 64.0 ** (1 / 2.5)], dtype=np.float32),
            label="numpy_array_float32",
        ),
        TestCase(
            value=xp.array([16.5, 81.2, 256.8]),
            a=1.9,
            expected=xp.array([16.5 ** (1 / 1.9), 81.2 ** (1 / 1.9), 256.8 ** (1 / 1.9)]),
            label="xp_array_float",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_power_inverse(self, test_case: TestCase) -> None:
        if expect_error(power_inverse, test_case.expected, test_case.value, test_case.a):
            return

        result = expect_warning(power_inverse, test_case.expected_warning, test_case.value, test_case.a)
        assert_array_equal(result, test_case.expected)
