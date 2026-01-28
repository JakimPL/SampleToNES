from dataclasses import dataclass
from typing import Any, Type, Union

import numpy as np
import pytest

from sampletones.constants.general import LIMIT_MAX_PITCH, LIMIT_MIN_PITCH, MAX_PERIOD, MAX_PITCH, MIN_PITCH
from sampletones.utils.frequencies import (
    clamp_period,
    clamp_pitch,
    frequency_to_pitch,
    is_pitch_valid,
    period_to_name,
    pitch_to_frequency,
    pitch_to_name,
    sanitize,
    sanitize_period,
    sanitize_pitch,
    validate_frequency,
    validate_period,
    validate_pitch,
)
from tests.sampletones.errors import expect_error


class TestValidatePitch:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        pitch: Any
        expected_result: Union[None, Type[Exception]]
        test_id: str

    test_cases = [
        TestCase(
            pitch=LIMIT_MIN_PITCH,
            expected_result=None,
            test_id="exactly_min_limit",
        ),
        TestCase(
            pitch=LIMIT_MAX_PITCH,
            expected_result=None,
            test_id="exactly_max_limit",
        ),
        TestCase(
            pitch=69,
            expected_result=None,
            test_id="middle_valid_pitch",
        ),
        TestCase(
            pitch=60,
            expected_result=None,
            test_id="another_valid_pitch",
        ),
        TestCase(
            pitch=(LIMIT_MIN_PITCH + LIMIT_MAX_PITCH) // 2,
            expected_result=None,
            test_id="middle_of_range",
        ),
        TestCase(
            pitch=LIMIT_MIN_PITCH - 1,
            expected_result=ValueError,
            test_id="one_below_min",
        ),
        TestCase(
            pitch=LIMIT_MAX_PITCH + 1,
            expected_result=ValueError,
            test_id="one_above_max",
        ),
        TestCase(
            pitch=0,
            expected_result=ValueError,
            test_id="zero",
        ),
        TestCase(
            pitch=-100,
            expected_result=ValueError,
            test_id="large_negative",
        ),
        TestCase(
            pitch=200,
            expected_result=ValueError,
            test_id="large_positive",
        ),
        TestCase(
            pitch="60",
            expected_result=TypeError,
            test_id="pitch_string",
        ),
        TestCase(
            pitch=None,
            expected_result=TypeError,
            test_id="pitch_none",
        ),
        TestCase(
            pitch=60.5,
            expected_result=TypeError,
            test_id="pitch_float",
        ),
        TestCase(
            pitch=[60],
            expected_result=TypeError,
            test_id="pitch_list",
        ),
        TestCase(
            pitch={"pitch": 60},
            expected_result=TypeError,
            test_id="pitch_dict",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_validate_pitch(self, test_case: TestCase) -> None:
        if expect_error(validate_pitch, test_case.expected_result, test_case.pitch):
            return

        validate_pitch(test_case.pitch)


class TestValidateFrequency:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        frequency: Any
        expected_result: Union[None, Type[Exception]]
        test_id: str

    test_cases = [
        TestCase(
            frequency=440.0,
            expected_result=None,
            test_id="valid_float",
        ),
        TestCase(
            frequency=440,
            expected_result=None,
            test_id="valid_int",
        ),
        TestCase(
            frequency=1.0,
            expected_result=None,
            test_id="one_hz",
        ),
        TestCase(
            frequency=0.001,
            expected_result=None,
            test_id="very_small_positive",
        ),
        TestCase(
            frequency=100000.0,
            expected_result=None,
            test_id="very_large_positive",
        ),
        TestCase(
            frequency=1e-100,
            expected_result=None,
            test_id="extremely_small_positive",
        ),
        TestCase(
            frequency=1e100,
            expected_result=None,
            test_id="extremely_large_positive",
        ),
        TestCase(
            frequency=0.0,
            expected_result=ValueError,
            test_id="zero",
        ),
        TestCase(
            frequency=-1.0,
            expected_result=ValueError,
            test_id="negative",
        ),
        TestCase(
            frequency=-440.0,
            expected_result=ValueError,
            test_id="negative_440",
        ),
        TestCase(
            frequency=np.inf,
            expected_result=ValueError,
            test_id="positive_infinity",
        ),
        TestCase(
            frequency=-np.inf,
            expected_result=ValueError,
            test_id="negative_infinity",
        ),
        TestCase(
            frequency=np.nan,
            expected_result=ValueError,
            test_id="nan",
        ),
        TestCase(
            frequency="440",
            expected_result=TypeError,
            test_id="frequency_string",
        ),
        TestCase(
            frequency=None,
            expected_result=TypeError,
            test_id="frequency_none",
        ),
        TestCase(
            frequency=[440.0],
            expected_result=TypeError,
            test_id="frequency_list",
        ),
        TestCase(
            frequency={"freq": 440.0},
            expected_result=TypeError,
            test_id="frequency_dict",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_validate_frequency(self, test_case: TestCase) -> None:
        if expect_error(validate_frequency, test_case.expected_result, test_case.frequency):
            return

        validate_frequency(test_case.frequency)


class TestIsPitchValid:
    def test_is_pitch_valid(self) -> None:
        valid_pitches = range(MIN_PITCH, MAX_PITCH + 1)
        for pitch in valid_pitches:
            assert is_pitch_valid(pitch), pitch

        invalid_pitches = (0, LIMIT_MIN_PITCH, MIN_PITCH - 1, MAX_PITCH + 1, LIMIT_MAX_PITCH, 128)
        for pitch in invalid_pitches:
            assert not is_pitch_valid(pitch), pitch


class TestValidatePeriod:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        period: Any
        expected_result: Union[None, Type[Exception]]
        test_id: str

    test_cases = [
        TestCase(
            period=0,
            expected_result=None,
            test_id="zero_minimum",
        ),
        TestCase(
            period=MAX_PERIOD,
            expected_result=None,
            test_id="exactly_max_period",
        ),
        TestCase(
            period=5,
            expected_result=None,
            test_id="middle_valid_period",
        ),
        TestCase(
            period=1,
            expected_result=None,
            test_id="one",
        ),
        TestCase(
            period=MAX_PERIOD - 1,
            expected_result=None,
            test_id="one_below_max",
        ),
        TestCase(
            period=MAX_PERIOD // 2,
            expected_result=None,
            test_id="middle_of_range",
        ),
        TestCase(
            period=-1,
            expected_result=ValueError,
            test_id="negative_one",
        ),
        TestCase(
            period=MAX_PERIOD + 1,
            expected_result=ValueError,
            test_id="one_above_max",
        ),
        TestCase(
            period=-100,
            expected_result=ValueError,
            test_id="large_negative",
        ),
        TestCase(
            period=100,
            expected_result=ValueError,
            test_id="large_positive",
        ),
        TestCase(
            period="5",
            expected_result=TypeError,
            test_id="period_string",
        ),
        TestCase(
            period=None,
            expected_result=TypeError,
            test_id="period_none",
        ),
        TestCase(
            period=5.5,
            expected_result=TypeError,
            test_id="period_float",
        ),
        TestCase(
            period=[5],
            expected_result=TypeError,
            test_id="period_list",
        ),
        TestCase(
            period={"period": 5},
            expected_result=TypeError,
            test_id="period_dict",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_validate_period(self, test_case: TestCase) -> None:
        if expect_error(validate_period, test_case.expected_result, test_case.period):
            return

        validate_period(test_case.period)


class TestPitchToFrequency:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        pitch: Any
        a4_frequency: Any
        a4_pitch: Any
        expected_result: Union[float, Type[Exception]]
        test_id: str

    test_cases = [
        TestCase(
            pitch=69,
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=440.0,
            test_id="a4_default_tuning",
        ),
        TestCase(
            pitch=81,
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=880.0,
            test_id="a5_one_octave_above",
        ),
        TestCase(
            pitch=57,
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=220.0,
            test_id="a3_one_octave_below",
        ),
        TestCase(
            pitch=60,
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=261.6255653005986,
            test_id="middle_c",
        ),
        TestCase(
            pitch=69,
            a4_frequency=432.0,
            a4_pitch=69,
            expected_result=432.0,
            test_id="a4_alternative_tuning",
        ),
        TestCase(
            pitch=69,
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=440.0,
            test_id="reference_pitch_returns_reference_frequency",
        ),
        TestCase(
            pitch=MIN_PITCH,
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=55.0,
            test_id="min_pitch_boundary",
        ),
        TestCase(
            pitch=MAX_PITCH,
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=7902.132820097988,
            test_id="max_pitch_boundary",
        ),
        TestCase(
            pitch=0,
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=ValueError,
            test_id="pitch_zero",
        ),
        TestCase(
            pitch=-12,
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=ValueError,
            test_id="negative_pitch",
        ),
        TestCase(
            pitch=127,
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=12543.853951415975,
            test_id="max_midi_pitch",
        ),
        TestCase(
            pitch=60,
            a4_frequency=432,
            a4_pitch=69,
            expected_result=256.86873684058776,
            test_id="middle_c_alternative_tuning",
        ),
        TestCase(
            pitch=60,
            a4_frequency=440.0,
            a4_pitch=60,
            expected_result=440.0,
            test_id="different_reference_pitch",
        ),
        TestCase(
            pitch=72,
            a4_frequency=440.0,
            a4_pitch=60,
            expected_result=880.0,
            test_id="octave_above_different_reference",
        ),
        TestCase(
            pitch=60,
            a4_frequency=880.0,
            a4_pitch=69,
            expected_result=523.2511306011972,
            test_id="double_reference_frequency",
        ),
        TestCase(
            pitch=69,
            a4_frequency=220.0,
            a4_pitch=69,
            expected_result=220.0,
            test_id="half_reference_frequency",
        ),
        TestCase(
            pitch="not_an_int",
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=TypeError,
            test_id="pitch_string",
        ),
        TestCase(
            pitch=None,
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=TypeError,
            test_id="pitch_none",
        ),
        TestCase(
            pitch=[60],
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=TypeError,
            test_id="pitch_list",
        ),
        TestCase(
            pitch={"pitch": 60},
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=TypeError,
            test_id="pitch_dict",
        ),
        TestCase(
            pitch=60,
            a4_frequency="440",
            a4_pitch=69,
            expected_result=TypeError,
            test_id="a4_frequency_string",
        ),
        TestCase(
            pitch=60,
            a4_frequency=None,
            a4_pitch=69,
            expected_result=TypeError,
            test_id="a4_frequency_none",
        ),
        TestCase(
            pitch=60,
            a4_frequency=[440.0],
            a4_pitch=69,
            expected_result=TypeError,
            test_id="a4_frequency_list",
        ),
        TestCase(
            pitch=60,
            a4_frequency=440.0,
            a4_pitch="69",
            expected_result=TypeError,
            test_id="a4_pitch_string",
        ),
        TestCase(
            pitch=60,
            a4_frequency=440.0,
            a4_pitch=None,
            expected_result=TypeError,
            test_id="a4_pitch_none",
        ),
        TestCase(
            pitch=60,
            a4_frequency=440.0,
            a4_pitch=[69],
            expected_result=TypeError,
            test_id="a4_pitch_list",
        ),
        TestCase(
            pitch=60,
            a4_frequency=np.inf,
            a4_pitch=69,
            expected_result=ValueError,
            test_id="a4_frequency_inf",
        ),
        TestCase(
            pitch=60,
            a4_frequency=-440.0,
            a4_pitch=69,
            expected_result=ValueError,
            test_id="a4_frequency_negative",
        ),
        TestCase(
            pitch=60,
            a4_frequency=0.0,
            a4_pitch=69,
            expected_result=ValueError,
            test_id="a4_frequency_zero",
        ),
        TestCase(
            pitch=60,
            a4_frequency=np.nan,
            a4_pitch=69,
            expected_result=ValueError,
            test_id="a4_frequency_nan",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_pitch_to_frequency(self, test_case: TestCase) -> None:
        if expect_error(
            pitch_to_frequency,
            test_case.expected_result,
            test_case.pitch,
            test_case.a4_frequency,
            test_case.a4_pitch,
        ):
            return

        result = pitch_to_frequency(test_case.pitch, test_case.a4_frequency, test_case.a4_pitch)
        if isinstance(test_case.expected_result, float) and np.isnan(test_case.expected_result):
            assert np.isnan(result)
        else:
            assert result == pytest.approx(test_case.expected_result, rel=1e-9)
            assert isinstance(result, float)


class TestFrequencyToPitch:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        frequency: Any
        a4_frequency: Any
        a4_pitch: Any
        expected_result: Union[int, Type[Exception]]
        test_id: str

    test_cases = [
        TestCase(
            frequency=440.0,
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=69,
            test_id="a4_frequency",
        ),
        TestCase(
            frequency=880.0,
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=81,
            test_id="a5_frequency",
        ),
        TestCase(
            frequency=261.63,
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=60,
            test_id="middle_c_approximate",
        ),
        TestCase(
            frequency=0.0,
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=ValueError,
            test_id="zero_frequency",
        ),
        TestCase(
            frequency=-100.0,
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=ValueError,
            test_id="negative_frequency",
        ),
        TestCase(
            frequency=220.0,
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=57,
            test_id="a3_frequency",
        ),
        TestCase(
            frequency=440.0,
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=69,
            test_id="reference_frequency_returns_reference_pitch",
        ),
        TestCase(
            frequency=55.0,
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=MIN_PITCH,
            test_id="min_frequency_boundary",
        ),
        TestCase(
            frequency=1e-10,
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=ValueError,
            test_id="very_small_positive_frequency",
        ),
        TestCase(
            frequency=100000.0,
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=ValueError,
            test_id="very_high_frequency",
        ),
        TestCase(
            frequency=432,
            a4_frequency=432,
            a4_pitch=69,
            expected_result=69,
            test_id="alternative_tuning",
        ),
        TestCase(
            frequency=440.0,
            a4_frequency=432,
            a4_pitch=69,
            expected_result=69,
            test_id="different_reference_frequency",
        ),
        TestCase(
            frequency=440,
            a4_frequency=440.0,
            a4_pitch=60,
            expected_result=60,
            test_id="different_reference_pitch",
        ),
        TestCase(
            frequency=880.0,
            a4_frequency=220.0,
            a4_pitch=69,
            expected_result=93,
            test_id="quadruple_reference_frequency",
        ),
        TestCase(
            frequency="440",
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=TypeError,
            test_id="frequency_string",
        ),
        TestCase(
            frequency=None,
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=TypeError,
            test_id="frequency_none",
        ),
        TestCase(
            frequency=[440.0],
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=TypeError,
            test_id="frequency_list",
        ),
        TestCase(
            frequency={"freq": 440.0},
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=TypeError,
            test_id="frequency_dict",
        ),
        TestCase(
            frequency=440.0,
            a4_frequency="440",
            a4_pitch=69,
            expected_result=TypeError,
            test_id="a4_frequency_string",
        ),
        TestCase(
            frequency=440.0,
            a4_frequency=None,
            a4_pitch=69,
            expected_result=TypeError,
            test_id="a4_frequency_none",
        ),
        TestCase(
            frequency=440.0,
            a4_frequency=440.0,
            a4_pitch="69",
            expected_result=TypeError,
            test_id="a4_pitch_string",
        ),
        TestCase(
            frequency=440.0,
            a4_frequency=440.0,
            a4_pitch=None,
            expected_result=TypeError,
            test_id="a4_pitch_none",
        ),
        TestCase(
            frequency=np.inf,
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=ValueError,
            test_id="frequency_inf",
        ),
        TestCase(
            frequency=-np.inf,
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=ValueError,
            test_id="frequency_negative_inf",
        ),
        TestCase(
            frequency=np.nan,
            a4_frequency=440.0,
            a4_pitch=69,
            expected_result=ValueError,
            test_id="frequency_nan",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_frequency_to_pitch(self, test_case: TestCase) -> None:
        if expect_error(
            frequency_to_pitch,
            test_case.expected_result,
            test_case.frequency,
            test_case.a4_frequency,
            test_case.a4_pitch,
        ):
            return

        result = frequency_to_pitch(test_case.frequency, test_case.a4_frequency, test_case.a4_pitch)
        assert result == test_case.expected_result
        assert isinstance(result, int)


class TestPitchToName:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        pitch: Any
        transpose: Any
        expected_result: Union[str, Type[Exception]]
        test_id: str

    test_cases = [
        TestCase(
            pitch=60,
            transpose=0,
            expected_result="C-3",
            test_id="middle_c",
        ),
        TestCase(
            pitch=69,
            transpose=0,
            expected_result="A-3",
            test_id="a3",
        ),
        TestCase(
            pitch=61,
            transpose=0,
            expected_result="C#3",
            test_id="c_sharp_3",
        ),
        TestCase(
            pitch=60,
            transpose=2,
            expected_result="D-3",
            test_id="middle_c_transpose_up_2",
        ),
        TestCase(
            pitch=60,
            transpose=-12,
            expected_result="C-2",
            test_id="middle_c_transpose_down_octave",
        ),
        TestCase(
            pitch=MIN_PITCH,
            transpose=0,
            expected_result="A-0",
            test_id="min_pitch",
        ),
        TestCase(
            pitch=MAX_PITCH,
            transpose=0,
            expected_result="B-7",
            test_id="max_pitch",
        ),
        TestCase(
            pitch=0,
            transpose=0,
            expected_result=ValueError,
            test_id="pitch_zero",
        ),
        TestCase(
            pitch=24,
            transpose=0,
            expected_result="C-0",
            test_id="minimum_valid_pitch",
        ),
        TestCase(
            pitch=-1,
            transpose=0,
            expected_result=ValueError,
            test_id="negative_pitch",
        ),
        TestCase(
            pitch=24,
            transpose=-1,
            expected_result=ValueError,
            test_id="invalid_pitch_after_transpose",
        ),
        TestCase(
            pitch=127,
            transpose=0,
            expected_result="G-8",
            test_id="max_midi_pitch",
        ),
        TestCase(
            pitch=60.0,
            transpose=12,
            expected_result=TypeError,
            test_id="pitch_float",
        ),
        TestCase(
            pitch=60,
            transpose=0.0,
            expected_result=TypeError,
            test_id="transpose_float",
        ),
        TestCase(
            pitch=60,
            transpose=None,
            expected_result=TypeError,
            test_id="transpose_none",
        ),
        TestCase(
            pitch=None,
            transpose=0,
            expected_result=TypeError,
            test_id="pitch_none",
        ),
        TestCase(
            pitch="60",
            transpose=0,
            expected_result=TypeError,
            test_id="pitch_string",
        ),
        TestCase(
            pitch=None,
            transpose=0,
            expected_result=TypeError,
            test_id="pitch_none",
        ),
        TestCase(
            pitch=[60],
            transpose=0,
            expected_result=TypeError,
            test_id="pitch_list",
        ),
        TestCase(
            pitch={"pitch": 60},
            transpose=0,
            expected_result=TypeError,
            test_id="pitch_dict",
        ),
        TestCase(
            pitch=60.5,
            transpose=0,
            expected_result=TypeError,
            test_id="pitch_float",
        ),
        TestCase(
            pitch=60,
            transpose="2",
            expected_result=TypeError,
            test_id="transpose_string",
        ),
        TestCase(
            pitch=60,
            transpose=None,
            expected_result=TypeError,
            test_id="transpose_none",
        ),
        TestCase(
            pitch=60,
            transpose=[2],
            expected_result=TypeError,
            test_id="transpose_list",
        ),
        TestCase(
            pitch=60,
            transpose=2.5,
            expected_result=TypeError,
            test_id="transpose_float",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_pitch_to_name(self, test_case: TestCase) -> None:
        if expect_error(pitch_to_name, test_case.expected_result, test_case.pitch, test_case.transpose):
            return

        result = pitch_to_name(test_case.pitch, test_case.transpose)
        assert result == test_case.expected_result


class TestPeriodToName:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        period: Any
        expected_result: Union[str, Type[Exception]]
        test_id: str

    test_cases = [
        TestCase(
            period=0,
            expected_result="0-#",
            test_id="period_0",
        ),
        TestCase(
            period=10,
            expected_result="A-#",
            test_id="period_10",
        ),
        TestCase(
            period=15,
            expected_result="F-#",
            test_id="period_15_max",
        ),
        TestCase(
            period=1,
            expected_result="1-#",
            test_id="period_1",
        ),
        TestCase(
            period=9,
            expected_result="9-#",
            test_id="period_9",
        ),
        TestCase(
            period=11,
            expected_result="B-#",
            test_id="period_11",
        ),
        TestCase(
            period=-1,
            expected_result=ValueError,
            test_id="period_negative",
        ),
        TestCase(
            period=100,
            expected_result=ValueError,
            test_id="period_too_large",
        ),
        TestCase(
            period="10",
            expected_result=TypeError,
            test_id="period_string",
        ),
        TestCase(
            period=None,
            expected_result=TypeError,
            test_id="period_none",
        ),
        TestCase(
            period=[10],
            expected_result=TypeError,
            test_id="period_list",
        ),
        TestCase(
            period={"period": 10},
            expected_result=TypeError,
            test_id="period_dict",
        ),
        TestCase(
            period=10.0,
            expected_result=TypeError,
            test_id="period_float",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_period_to_name(self, test_case: TestCase) -> None:
        if expect_error(period_to_name, test_case.expected_result, test_case.period):
            return

        result = period_to_name(test_case.period)
        assert result == test_case.expected_result


class TestClampPitch:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        pitch: Any
        min_pitch: Any
        max_pitch: Any
        expected_result: Union[int, Type[Exception]]
        test_id: str

    test_cases = [
        TestCase(
            pitch=60,
            min_pitch=MIN_PITCH,
            max_pitch=MAX_PITCH,
            expected_result=60,
            test_id="within_range",
        ),
        TestCase(
            pitch=0,
            min_pitch=MIN_PITCH,
            max_pitch=MAX_PITCH,
            expected_result=MIN_PITCH,
            test_id="below_minimum",
        ),
        TestCase(
            pitch=150,
            min_pitch=MIN_PITCH,
            max_pitch=MAX_PITCH,
            expected_result=MAX_PITCH,
            test_id="above_maximum",
        ),
        TestCase(
            pitch=MIN_PITCH,
            min_pitch=MIN_PITCH,
            max_pitch=MAX_PITCH,
            expected_result=MIN_PITCH,
            test_id="exactly_minimum",
        ),
        TestCase(
            pitch=MAX_PITCH,
            min_pitch=MIN_PITCH,
            max_pitch=MAX_PITCH,
            expected_result=MAX_PITCH,
            test_id="exactly_maximum",
        ),
        TestCase(
            pitch=-100,
            min_pitch=MIN_PITCH,
            max_pitch=MAX_PITCH,
            expected_result=MIN_PITCH,
            test_id="large_negative",
        ),
        TestCase(
            pitch=1000,
            min_pitch=MIN_PITCH,
            max_pitch=MAX_PITCH,
            expected_result=MAX_PITCH,
            test_id="large_positive",
        ),
        TestCase(
            pitch=60,
            min_pitch=50,
            max_pitch=70,
            expected_result=60,
            test_id="custom_range_within",
        ),
        TestCase(
            pitch=40,
            min_pitch=50,
            max_pitch=70,
            expected_result=50,
            test_id="custom_range_below",
        ),
        TestCase(
            pitch=80,
            min_pitch=50,
            max_pitch=70,
            expected_result=70,
            test_id="custom_range_above",
        ),
        TestCase(
            pitch=60,
            min_pitch=LIMIT_MIN_PITCH,
            max_pitch=LIMIT_MAX_PITCH,
            expected_result=60,
            test_id="possible_range",
        ),
        TestCase(
            pitch=60,
            min_pitch=60,
            max_pitch=60,
            expected_result=60,
            test_id="single_value_range",
        ),
        TestCase(
            pitch=10,
            min_pitch=60,
            max_pitch=60,
            expected_result=60,
            test_id="single_value_range_outside",
        ),
        TestCase(
            pitch=32,
            min_pitch=40,
            max_pitch=30,
            expected_result=ValueError,
            test_id="min_greater_than_max",
        ),
        TestCase(
            pitch="60",
            min_pitch=MIN_PITCH,
            max_pitch=MAX_PITCH,
            expected_result=TypeError,
            test_id="pitch_string",
        ),
        TestCase(
            pitch=None,
            min_pitch=MIN_PITCH,
            max_pitch=MAX_PITCH,
            expected_result=TypeError,
            test_id="pitch_none",
        ),
        TestCase(
            pitch=[60],
            min_pitch=MIN_PITCH,
            max_pitch=MAX_PITCH,
            expected_result=TypeError,
            test_id="pitch_list",
        ),
        TestCase(
            pitch=60,
            min_pitch="33",
            max_pitch=MAX_PITCH,
            expected_result=TypeError,
            test_id="min_pitch_string",
        ),
        TestCase(
            pitch=60,
            min_pitch=MIN_PITCH,
            max_pitch="119",
            expected_result=TypeError,
            test_id="max_pitch_string",
        ),
        TestCase(
            pitch=60,
            min_pitch=None,
            max_pitch=MAX_PITCH,
            expected_result=TypeError,
            test_id="min_pitch_none",
        ),
        TestCase(
            pitch=60,
            min_pitch=MIN_PITCH,
            max_pitch=None,
            expected_result=TypeError,
            test_id="max_pitch_none",
        ),
        TestCase(
            pitch=60.0,
            min_pitch=MIN_PITCH,
            max_pitch=MAX_PITCH,
            expected_result=TypeError,
            test_id="pitch_float",
        ),
        TestCase(
            pitch=60,
            min_pitch=MIN_PITCH,
            max_pitch=LIMIT_MAX_PITCH + 1,
            expected_result=ValueError,
            test_id="max_pitch_out_of_bounds",
        ),
        TestCase(
            pitch=60,
            min_pitch=LIMIT_MIN_PITCH - 1,
            max_pitch=LIMIT_MAX_PITCH,
            expected_result=ValueError,
            test_id="min_pitch_out_of_bounds",
        ),
        TestCase(
            pitch=60,
            min_pitch=LIMIT_MIN_PITCH,
            max_pitch=LIMIT_MAX_PITCH + 1,
            expected_result=ValueError,
            test_id="max_pitch_out_of_bounds",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_clamp_pitch(self, test_case: TestCase) -> None:
        if expect_error(
            clamp_pitch, test_case.expected_result, test_case.pitch, test_case.min_pitch, test_case.max_pitch
        ):
            return

        result = clamp_pitch(test_case.pitch, test_case.min_pitch, test_case.max_pitch)
        assert result == test_case.expected_result
        assert isinstance(result, int)


class TestClampPeriod:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        period: Any
        expected_result: Union[int, Type[Exception]]
        test_id: str

    test_cases = [
        TestCase(
            period=5,
            expected_result=5,
            test_id="within_range",
        ),
        TestCase(
            period=-10,
            expected_result=0,
            test_id="below_minimum",
        ),
        TestCase(
            period=100,
            expected_result=MAX_PERIOD,
            test_id="above_maximum",
        ),
        TestCase(
            period=0,
            expected_result=0,
            test_id="exactly_minimum",
        ),
        TestCase(
            period=MAX_PERIOD,
            expected_result=MAX_PERIOD,
            test_id="exactly_maximum",
        ),
        TestCase(
            period=-1000,
            expected_result=0,
            test_id="large_negative",
        ),
        TestCase(
            period=1000,
            expected_result=MAX_PERIOD,
            test_id="large_positive",
        ),
        TestCase(
            period="5",
            expected_result=TypeError,
            test_id="period_string",
        ),
        TestCase(
            period=None,
            expected_result=TypeError,
            test_id="period_none",
        ),
        TestCase(
            period=[5],
            expected_result=TypeError,
            test_id="period_list",
        ),
        TestCase(
            period=5.0,
            expected_result=5,
            test_id="period_float",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_clamp_period(self, test_case: TestCase) -> None:
        if expect_error(
            clamp_period,
            test_case.expected_result,
            test_case.period,
        ):
            return

        result = clamp_period(test_case.period)
        assert result == test_case.expected_result
        assert isinstance(result, int)


class TestSanitize:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        name: Any
        expected_result: Union[str, Type[Exception]]
        test_id: str

    test_cases = [
        TestCase(
            name="  hello world  ",
            expected_result="HELLO WORLD",
            test_id="strip_and_uppercase",
        ),
        TestCase(
            name="c#4",
            expected_result="C#4",
            test_id="lowercase_to_uppercase",
        ),
        TestCase(
            name="  A4  ",
            expected_result="A4",
            test_id="strip_whitespace",
        ),
        TestCase(
            name="ALREADY UPPER",
            expected_result="ALREADY UPPER",
            test_id="already_uppercase",
        ),
        TestCase(
            name="",
            expected_result="",
            test_id="empty_string",
        ),
        TestCase(
            name="   ",
            expected_result="",
            test_id="only_whitespace",
        ),
        TestCase(
            name="MiXeD CaSe",
            expected_result="MIXED CASE",
            test_id="mixed_case",
        ),
        TestCase(
            name="\t\n  test  \n\t",
            expected_result="TEST",
            test_id="various_whitespace",
        ),
        TestCase(
            name="a",
            expected_result="A",
            test_id="single_character",
        ),
        TestCase(
            name="123",
            expected_result="123",
            test_id="digits_only",
        ),
        TestCase(
            name="special!@#$%^&*()",
            expected_result="SPECIAL!@#$%^&*()",
            test_id="special_characters",
        ),
        TestCase(
            name=None,
            expected_result=AttributeError,
            test_id="name_none",
        ),
        TestCase(
            name=123,
            expected_result=AttributeError,
            test_id="name_int",
        ),
        TestCase(
            name=["test"],
            expected_result=AttributeError,
            test_id="name_list",
        ),
        TestCase(
            name={"name": "test"},
            expected_result=AttributeError,
            test_id="name_dict",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_sanitize(self, test_case: TestCase) -> None:
        if expect_error(sanitize, test_case.expected_result, test_case.name):
            return

        result = sanitize(test_case.name)
        assert result == test_case.expected_result


class TestSanitizePitch:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        name: Any
        expected_result: Union[str, Type[Exception]]
        test_id: str

    test_cases = [
        TestCase(
            name="C#4",
            expected_result="C#4",
            test_id="valid_pitch_name",
        ),
        TestCase(
            name="  a#3  ",
            expected_result="A#3",
            test_id="lowercase_with_whitespace",
        ),
        TestCase(
            name="C@4!",
            expected_result="C4",
            test_id="invalid_characters_removed",
        ),
        TestCase(
            name="F-#",
            expected_result="F-#",
            test_id="period_format",
        ),
        TestCase(
            name="",
            expected_result="",
            test_id="empty_string",
        ),
        TestCase(
            name="xyz",
            expected_result="",
            test_id="no_valid_characters",
        ),
        TestCase(
            name="A0",
            expected_result="A0",
            test_id="note_with_octave",
        ),
        TestCase(
            name="D#5",
            expected_result="D#5",
            test_id="sharp_note",
        ),
        TestCase(
            name="123456789",
            expected_result="123456789",
            test_id="all_digits",
        ),
        TestCase(
            name="ABCDEF",
            expected_result="ABCDEF",
            test_id="all_hex_letters",
        ),
        TestCase(
            name="0-#",
            expected_result="0-#",
            test_id="period_format_0",
        ),
        TestCase(
            name="a#3 test",
            expected_result="A#3E",
            test_id="extra_text_a-f_stayed",
        ),
        TestCase(
            name="G--",
            expected_result="--",
            test_id="multiple_hyphens_g_removed",
        ),
        TestCase(
            name="C##4",
            expected_result="C##4",
            test_id="double_sharp",
        ),
        TestCase(
            name=None,
            expected_result=AttributeError,
            test_id="name_none",
        ),
        TestCase(
            name=123,
            expected_result=AttributeError,
            test_id="name_int",
        ),
        TestCase(
            name=["C#4"],
            expected_result=AttributeError,
            test_id="name_list",
        ),
        TestCase(
            name={"name": "C#4"},
            expected_result=AttributeError,
            test_id="name_dict",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_sanitize_pitch(self, test_case: TestCase) -> None:
        if expect_error(sanitize_pitch, test_case.expected_result, test_case.name):
            return

        result = sanitize_pitch(test_case.name)
        assert result == test_case.expected_result


class TestSanitizePeriod:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        name: Any
        expected_result: Union[str, Type[Exception]]
        test_id: str

    test_cases = [
        TestCase(
            name="0A",
            expected_result="0A",
            test_id="hex_digits",
        ),
        TestCase(
            name="  f  ",
            expected_result="F",
            test_id="lowercase_with_whitespace",
        ),
        TestCase(
            name="A-#",
            expected_result="A",
            test_id="period_format_stripped",
        ),
        TestCase(
            name="10@!",
            expected_result="10",
            test_id="invalid_characters_removed",
        ),
        TestCase(
            name="",
            expected_result="",
            test_id="empty_string",
        ),
        TestCase(
            name="xyz",
            expected_result="",
            test_id="no_valid_characters",
        ),
        TestCase(
            name="123456789",
            expected_result="123456789",
            test_id="all_digits",
        ),
        TestCase(
            name="ABCDEF",
            expected_result="ABCDEF",
            test_id="all_hex_letters",
        ),
        TestCase(
            name="0123456789ABCDEF",
            expected_result="0123456789ABCDEF",
            test_id="all_hex_characters",
        ),
        TestCase(
            name="ghijklmnop",
            expected_result="",
            test_id="non_hex_letters",
        ),
        TestCase(
            name="F-#",
            expected_result="F",
            test_id="f_period_format",
        ),
        TestCase(
            name="1a2b3c",
            expected_result="1A2B3C",
            test_id="mixed_hex",
        ),
        TestCase(
            name="!@#$%^&*()",
            expected_result="",
            test_id="only_special_characters",
        ),
        TestCase(
            name="   ",
            expected_result="",
            test_id="only_whitespace",
        ),
        TestCase(
            name=None,
            expected_result=AttributeError,
            test_id="name_none",
        ),
        TestCase(
            name=123,
            expected_result=AttributeError,
            test_id="name_int",
        ),
        TestCase(
            name=["0A"],
            expected_result=AttributeError,
            test_id="name_list",
        ),
        TestCase(
            name={"name": "0A"},
            expected_result=AttributeError,
            test_id="name_dict",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_sanitize_period(self, test_case: TestCase) -> None:
        if expect_error(sanitize_period, test_case.expected_result, test_case.name):
            return

        result = sanitize_period(test_case.name)
        assert result == test_case.expected_result
