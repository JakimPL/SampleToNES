from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import numpy as np
import pytest

from sampletones import xp
from sampletones.utils.transformations.functions import energy, exp, identity, power, power_inverse
from tests.sampletones.arrays import assert_array_equal
from tests.sampletones.errors import expect_error, expect_warning


class TestIdentity:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        value: Any
        expected_result: Any
        test_id: str

    test_cases = [
        TestCase(
            value=True,
            expected_result=True,
            test_id="bool_true",
        ),
        TestCase(
            value=False,
            expected_result=False,
            test_id="bool_false",
        ),
        TestCase(
            value=0,
            expected_result=0,
            test_id="int_zero",
        ),
        TestCase(
            value=42,
            expected_result=42,
            test_id="int_positive",
        ),
        TestCase(
            value=-17,
            expected_result=-17,
            test_id="int_negative",
        ),
        TestCase(
            value=0.0,
            expected_result=0.0,
            test_id="float_zero",
        ),
        TestCase(
            value=3.14,
            expected_result=3.14,
            test_id="float_positive",
        ),
        TestCase(
            value=-2.718,
            expected_result=-2.718,
            test_id="float_negative",
        ),
        TestCase(
            value=np.int32(100),
            expected_result=np.int32(100),
            test_id="numpy_int32",
        ),
        TestCase(
            value=np.int64(-256),
            expected_result=np.int64(-256),
            test_id="numpy_int64",
        ),
        TestCase(
            value=np.float32(1.5),
            expected_result=np.float32(1.5),
            test_id="numpy_float32",
        ),
        TestCase(
            value=np.float64(2.5),
            expected_result=np.float64(2.5),
            test_id="numpy_float64",
        ),
        TestCase(
            value=xp.int32(7),
            expected_result=xp.int32(7),
            test_id="xp_int32",
        ),
        TestCase(
            value=xp.int64(-999),
            expected_result=xp.int64(-999),
            test_id="xp_int64",
        ),
        TestCase(
            value=xp.float32(3.14),
            expected_result=xp.float32(3.14),
            test_id="xp_float32",
        ),
        TestCase(
            value=xp.float64(-1.23),
            expected_result=xp.float64(-1.23),
            test_id="xp_float64",
        ),
        TestCase(
            value=np.array([1, 2, 3]),
            expected_result=np.array([1, 2, 3]),
            test_id="numpy_array_int",
        ),
        TestCase(
            value=np.array([1.5, 2.5, 3.5], dtype=np.float32),
            expected_result=np.array([1.5, 2.5, 3.5], dtype=np.float32),
            test_id="numpy_array_float32",
        ),
        TestCase(
            value=xp.array([4, 5, 6]),
            expected_result=xp.array([4, 5, 6]),
            test_id="xp_array_int",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_identity(self, test_case: TestCase) -> None:
        result = identity(test_case.value)
        assert_array_equal(result, test_case.expected_result)


class TestEnergy:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        value: Any
        expected_result: Any
        test_id: str

    test_cases = [
        TestCase(
            value=True,
            expected_result=np.int8(1),
            test_id="bool_true",
        ),
        TestCase(
            value=False,
            expected_result=np.int8(0),
            test_id="bool_false",
        ),
        TestCase(
            value=0,
            expected_result=np.int64(0),
            test_id="int_zero",
        ),
        TestCase(
            value=3,
            expected_result=np.int64(9),
            test_id="int_positive",
        ),
        TestCase(
            value=-4,
            expected_result=np.int64(16),
            test_id="int_negative",
        ),
        TestCase(
            value=0.0,
            expected_result=np.float64(0.0),
            test_id="float_zero",
        ),
        TestCase(
            value=2.0,
            expected_result=np.float64(4.0),
            test_id="float_positive",
        ),
        TestCase(
            value=-3.0,
            expected_result=np.float64(9.0),
            test_id="float_negative",
        ),
        TestCase(
            value=0.5,
            expected_result=np.float64(0.25),
            test_id="float_fractional",
        ),
        TestCase(
            value=np.int32(5),
            expected_result=np.int32(25),
            test_id="numpy_int32",
        ),
        TestCase(
            value=np.int64(-10),
            expected_result=np.int64(100),
            test_id="numpy_int64",
        ),
        TestCase(
            value=np.float32(2.5),
            expected_result=np.float32(6.25),
            test_id="numpy_float32",
        ),
        TestCase(
            value=np.float64(-1.5),
            expected_result=np.float64(2.25),
            test_id="numpy_float64",
        ),
        TestCase(
            value=xp.int32(6),
            expected_result=xp.int32(36),
            test_id="xp_int32",
        ),
        TestCase(
            value=xp.int64(-8),
            expected_result=xp.int64(64),
            test_id="xp_int64",
        ),
        TestCase(
            value=xp.float32(1.5),
            expected_result=xp.float32(2.25),
            test_id="xp_float32",
        ),
        TestCase(
            value=xp.float64(-2.5),
            expected_result=xp.float64(6.25),
            test_id="xp_float64",
        ),
        TestCase(
            value=np.array([2.5, 3.2, 4.1]),
            expected_result=np.array([6.25, 10.24, 16.81]),
            test_id="numpy_array_float",
        ),
        TestCase(
            value=np.array([1.0, 2.0, 3.0], dtype=np.float32),
            expected_result=np.array([1.0, 4.0, 9.0], dtype=np.float32),
            test_id="numpy_array_float32",
        ),
        TestCase(
            value=xp.array([-2.5, -3.0, -4.2]),
            expected_result=xp.array([6.25, 9.0, 17.64]),
            test_id="xp_array_float",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_energy(self, test_case: TestCase) -> None:
        result = energy(test_case.value)
        assert_array_equal(result, test_case.expected_result)


class TestExp:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        value: Any
        expected_result: Any
        test_id: str

    test_cases = [
        TestCase(
            value=True,
            expected_result=np.float16(np.e),
            test_id="bool_true",
        ),
        TestCase(
            value=False,
            expected_result=np.float16(1.0),
            test_id="bool_false",
        ),
        TestCase(
            value=0,
            expected_result=np.float64(1.0),
            test_id="int_zero",
        ),
        TestCase(
            value=1,
            expected_result=np.float64(np.e),
            test_id="int_one",
        ),
        TestCase(
            value=2,
            expected_result=np.float64(np.e**2),
            test_id="int_two",
        ),
        TestCase(
            value=-1,
            expected_result=np.float64(1.0 / np.e),
            test_id="int_negative_one",
        ),
        TestCase(
            value=0.0,
            expected_result=np.float64(1.0),
            test_id="float_zero",
        ),
        TestCase(
            value=1.0,
            expected_result=np.float64(np.e),
            test_id="float_one",
        ),
        TestCase(
            value=-1.0,
            expected_result=np.float64(1.0 / np.e),
            test_id="float_negative_one",
        ),
        TestCase(
            value=0.5,
            expected_result=np.float64(np.e**0.5),
            test_id="float_half",
        ),
        TestCase(
            value=np.int32(0),
            expected_result=np.float64(1.0),
            test_id="numpy_int32_zero",
        ),
        TestCase(
            value=np.int64(2),
            expected_result=np.float64(np.e**2),
            test_id="numpy_int64",
        ),
        TestCase(
            value=np.float32(1.0),
            expected_result=np.float32(np.e),
            test_id="numpy_float32",
        ),
        TestCase(
            value=np.float64(-0.5),
            expected_result=np.float64(np.e**-0.5),
            test_id="numpy_float64",
        ),
        TestCase(
            value=xp.int32(1),
            expected_result=np.float64(np.e),
            test_id="xp_int32",
        ),
        TestCase(
            value=xp.int64(-1),
            expected_result=np.float64(1.0 / np.e),
            test_id="xp_int64",
        ),
        TestCase(
            value=xp.float32(2.0),
            expected_result=xp.float32(np.e**2),
            test_id="xp_float32",
        ),
        TestCase(
            value=xp.float64(0.5),
            expected_result=xp.float64(np.e**0.5),
            test_id="xp_float64",
        ),
        TestCase(
            value=np.array([0.5, 1.2, 2.3]),
            expected_result=np.array([np.e**0.5, np.e**1.2, np.e**2.3]),
            test_id="numpy_array_float",
        ),
        TestCase(
            value=np.array([0.0, 1.0, -1.0], dtype=np.float32),
            expected_result=np.array([1.0, np.e, 1.0 / np.e], dtype=np.float32),
            test_id="numpy_array_float32",
        ),
        TestCase(
            value=xp.array([1.5, 2.7, 3.1]),
            expected_result=xp.array([np.e**1.5, np.e**2.7, np.e**3.1]),
            test_id="xp_array_float",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_exp(self, test_case: TestCase) -> None:
        result = exp(test_case.value)
        assert_array_equal(result, test_case.expected_result)


class TestPower:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        value: Any
        a: float
        expected_result: Any
        test_id: str
        expected_warning: Any = None

    test_cases = [
        TestCase(
            value=True,
            a=2.0,
            expected_result=np.float64(1.0),
            test_id="bool_true",
        ),
        TestCase(
            value=False,
            a=2.0,
            expected_result=np.float64(0.0),
            test_id="bool_false",
        ),
        TestCase(
            value=2,
            a=0.0,
            expected_result=np.float64(1.0),
            test_id="int_power_zero",
        ),
        TestCase(
            value=0,
            a=2.0,
            expected_result=np.float64(0.0),
            test_id="int_zero_base",
        ),
        TestCase(
            value=0,
            a=0.0,
            expected_result=np.float64(1.0),
            test_id="int_zero_base_zero_power",
        ),
        TestCase(
            value=2,
            a=3.0,
            expected_result=np.float64(8.0),
            test_id="int_positive",
        ),
        TestCase(
            value=2,
            a=-2.0,
            expected_result=np.float64(0.25),
            test_id="int_negative_exponent",
        ),
        TestCase(
            value=-2,
            a=2.0,
            expected_result=np.float64(4.0),
            test_id="int_negative_base_even_power",
        ),
        TestCase(
            value=-2,
            a=3.0,
            expected_result=np.float64(-8.0),
            test_id="int_negative_base_odd_power",
        ),
        TestCase(
            value=4.0,
            a=0.5,
            expected_result=np.float64(2.0),
            test_id="float_square_root",
        ),
        TestCase(
            value=2.0,
            a=0.0,
            expected_result=np.float64(1.0),
            test_id="float_power_zero",
        ),
        TestCase(
            value=0.0,
            a=2.0,
            expected_result=np.float64(0.0),
            test_id="float_zero_base",
        ),
        TestCase(
            value=0.0,
            a=0.0,
            expected_result=np.float64(1.0),
            test_id="float_zero_base_zero_power",
        ),
        TestCase(
            value=3.0,
            a=2.0,
            expected_result=np.float64(9.0),
            test_id="float_positive",
        ),
        TestCase(
            value=2.0,
            a=-1.0,
            expected_result=np.float64(0.5),
            test_id="float_negative_exponent",
        ),
        TestCase(
            value=np.int32(3),
            a=2.0,
            expected_result=np.float64(9.0),
            test_id="numpy_int32",
        ),
        TestCase(
            value=np.int64(2),
            a=3.0,
            expected_result=np.float64(8.0),
            test_id="numpy_int64",
        ),
        TestCase(
            value=np.float32(2.0),
            a=3.0,
            expected_result=np.float32(8.0),
            test_id="numpy_float32",
        ),
        TestCase(
            value=np.float64(4.0),
            a=0.5,
            expected_result=np.float64(2.0),
            test_id="numpy_float64",
        ),
        TestCase(
            value=xp.int32(5),
            a=2.0,
            expected_result=np.float64(25.0),
            test_id="xp_int32",
        ),
        TestCase(
            value=xp.int64(3),
            a=3.0,
            expected_result=np.float64(27.0),
            test_id="xp_int64",
        ),
        TestCase(
            value=xp.float32(2.0),
            a=4.0,
            expected_result=xp.float32(16.0),
            test_id="xp_float32",
        ),
        TestCase(
            value=xp.float64(9.0),
            a=0.5,
            expected_result=xp.float64(3.0),
            test_id="xp_float64",
        ),
        TestCase(
            value=2.0,
            a=2.5,
            expected_result=np.float64(2.0**2.5),
            test_id="float_non_integer_exponent",
        ),
        TestCase(
            value=8,
            a=1.333333333,
            expected_result=np.float64(8**1.333333333),
            test_id="int_fractional_exponent",
        ),
        TestCase(
            value=3.5,
            a=-1.7,
            expected_result=np.float64(3.5**-1.7),
            test_id="float_negative_fractional_exponent",
        ),
        TestCase(
            value=0.5,
            a=2.3,
            expected_result=np.float64(0.5**2.3),
            test_id="fractional_base_non_integer_exponent",
        ),
        TestCase(
            value=-2.0,
            a=2.5,
            expected_result=np.float64(float("nan")),
            test_id="negative_base_non_integer_exponent_nan",
            expected_warning=RuntimeWarning,
        ),
        TestCase(
            value=np.float32(4.0),
            a=1.5,
            expected_result=np.float32(8.0),
            test_id="numpy_float32_non_integer_exponent",
        ),
        TestCase(
            value=-1,
            a=-1.0,
            expected_result=np.float64(-1.0),
            test_id="negative_one_to_negative_one",
        ),
        TestCase(
            value=-3,
            a=-2.0,
            expected_result=np.float64(1.0 / 9.0),
            test_id="negative_int_negative_even_power",
        ),
        TestCase(
            value=-3,
            a=-3.0,
            expected_result=np.float64(-1.0 / 27.0),
            test_id="negative_int_negative_odd_power",
        ),
        TestCase(
            value=np.array([2, 3, 4]),
            a=2.0,
            expected_result=np.array([4.0, 9.0, 16.0]),
            test_id="numpy_array_int",
        ),
        TestCase(
            value=np.array([1.0, 2.0, 3.0], dtype=np.float32),
            a=3.0,
            expected_result=np.array([1.0, 8.0, 27.0], dtype=np.float32),
            test_id="numpy_array_float32_integer_power",
        ),
        TestCase(
            value=np.array([2.5, 3.0, 4.2]),
            a=1.8,
            expected_result=np.array([2.5**1.8, 3.0**1.8, 4.2**1.8]),
            test_id="numpy_array_float",
        ),
        TestCase(
            value=np.array([1.5, 2.0, 3.5], dtype=np.float32),
            a=2.3,
            expected_result=np.array([1.5**2.3, 2.0**2.3, 3.5**2.3], dtype=np.float32),
            test_id="numpy_array_float32",
        ),
        TestCase(
            value=xp.array([2.2, 4.5, 8.1]),
            a=0.7,
            expected_result=xp.array([2.2**0.7, 4.5**0.7, 8.1**0.7]),
            test_id="xp_array_float",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_power(self, test_case: TestCase) -> None:
        result = expect_warning(power, test_case.expected_warning, test_case.value, test_case.a)
        assert_array_equal(result, test_case.expected_result)


class TestPowerInverse:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        value: Any
        a: float
        expected_result: Any
        test_id: str
        expected_warning: Optional[Any] = None

    test_cases = [
        TestCase(
            value=True,
            a=2.0,
            expected_result=np.float64(1.0),
            test_id="bool_true",
        ),
        TestCase(
            value=False,
            a=2.0,
            expected_result=np.float64(0.0),
            test_id="bool_false",
        ),
        TestCase(
            value=2,
            a=0.0,
            expected_result=ZeroDivisionError,
            test_id="int_power_inverse_zero_inf",
        ),
        TestCase(
            value=0,
            a=0.0,
            expected_result=ZeroDivisionError,
            test_id="zero_base_power_inverse_zero_nan",
        ),
        TestCase(
            value=8,
            a=3.0,
            expected_result=np.float64(2.0),
            test_id="int_cube_root",
        ),
        TestCase(
            value=0,
            a=2.0,
            expected_result=np.float64(0.0),
            test_id="int_zero_base",
        ),
        TestCase(
            value=16,
            a=2.0,
            expected_result=np.float64(4.0),
            test_id="int_square_root",
        ),
        TestCase(
            value=4,
            a=-2.0,
            expected_result=np.float64(0.5),
            test_id="int_negative_exponent",
        ),
        TestCase(
            value=4.0,
            a=2.0,
            expected_result=np.float64(2.0),
            test_id="float_square_root",
        ),
        TestCase(
            value=0.0,
            a=2.0,
            expected_result=np.float64(0.0),
            test_id="float_zero_base",
        ),
        TestCase(
            value=27.0,
            a=3.0,
            expected_result=np.float64(3.0),
            test_id="float_cube_root",
        ),
        TestCase(
            value=2.0,
            a=-1.0,
            expected_result=np.float64(0.5),
            test_id="float_negative_exponent",
        ),
        TestCase(
            value=np.int32(16),
            a=2.0,
            expected_result=np.float64(4.0),
            test_id="numpy_int32",
        ),
        TestCase(
            value=np.int64(8),
            a=3.0,
            expected_result=np.float64(2.0),
            test_id="numpy_int64",
        ),
        TestCase(
            value=np.float32(9.0),
            a=2.0,
            expected_result=np.float32(3.0),
            test_id="numpy_float32",
        ),
        TestCase(
            value=np.float64(16.0),
            a=4.0,
            expected_result=np.float64(2.0),
            test_id="numpy_float64",
        ),
        TestCase(
            value=xp.int32(25),
            a=2.0,
            expected_result=np.float64(5.0),
            test_id="xp_int32",
        ),
        TestCase(
            value=xp.int64(27),
            a=3.0,
            expected_result=np.float64(3.0),
            test_id="xp_int64",
        ),
        TestCase(
            value=xp.float32(16.0),
            a=2.0,
            expected_result=xp.float32(4.0),
            test_id="xp_float32",
        ),
        TestCase(
            value=xp.float64(8.0),
            a=3.0,
            expected_result=xp.float64(2.0),
            test_id="xp_float64",
        ),
        TestCase(
            value=32.0,
            a=2.5,
            expected_result=np.float64(32.0 ** (1 / 2.5)),
            test_id="float_non_integer_exponent",
        ),
        TestCase(
            value=100,
            a=1.5,
            expected_result=np.float64(100 ** (1 / 1.5)),
            test_id="int_fractional_exponent",
        ),
        TestCase(
            value=5.0,
            a=-1.3,
            expected_result=np.float64(5.0 ** (1 / -1.3)),
            test_id="float_negative_fractional_exponent",
        ),
        TestCase(
            value=0.25,
            a=1.8,
            expected_result=np.float64(0.25 ** (1 / 1.8)),
            test_id="fractional_base_non_integer_exponent",
        ),
        TestCase(
            value=np.float32(16.0),
            a=2.4,
            expected_result=np.float32(16.0 ** (1 / 2.4)),
            test_id="numpy_float32_non_integer_exponent",
        ),
        TestCase(
            value=-1,
            a=-1.0,
            expected_result=np.float64(-1.0),
            test_id="negative_one_exponent_negative_one",
        ),
        TestCase(
            value=-8,
            a=3.0,
            expected_result=np.float64(np.nan),
            test_id="negative_int_odd_exponent",
            expected_warning=RuntimeWarning,
        ),
        TestCase(
            value=np.array([4, 9, 16]),
            a=2.0,
            expected_result=np.array([2.0, 3.0, 4.0]),
            test_id="numpy_array_int",
        ),
        TestCase(
            value=np.array([8.0, 27.0, 64.0], dtype=np.float32),
            a=3.0,
            expected_result=np.array([2.0, 3.0, 4.0], dtype=np.float32),
            test_id="numpy_array_float32_integer_exponent",
        ),
        TestCase(
            value=np.array([6.25, 10.24, 16.81]),
            a=1.7,
            expected_result=np.array([6.25 ** (1 / 1.7), 10.24 ** (1 / 1.7), 16.81 ** (1 / 1.7)]),
            test_id="numpy_array_float",
        ),
        TestCase(
            value=np.array([8.0, 27.0, 64.0], dtype=np.float32),
            a=2.5,
            expected_result=np.array([8.0 ** (1 / 2.5), 27.0 ** (1 / 2.5), 64.0 ** (1 / 2.5)], dtype=np.float32),
            test_id="numpy_array_float32",
        ),
        TestCase(
            value=xp.array([16.5, 81.2, 256.8]),
            a=1.9,
            expected_result=xp.array([16.5 ** (1 / 1.9), 81.2 ** (1 / 1.9), 256.8 ** (1 / 1.9)]),
            test_id="xp_array_float",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_power_inverse(self, test_case: TestCase) -> None:
        if expect_error(power_inverse, test_case.expected_result, test_case.value, test_case.a):
            return

        result = expect_warning(power_inverse, test_case.expected_warning, test_case.value, test_case.a)
        assert_array_equal(result, test_case.expected_result)
