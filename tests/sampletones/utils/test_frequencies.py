from dataclasses import dataclass
from typing import Any, Type, Union

import numpy as np
import pytest

from sampletones.constants.general import MAX_PITCH, MIN_PITCH
from sampletones.utils.frequencies import (
    frequency_to_pitch,
    pitch_to_frequency,
)
from tests.sampletones.errors import expect_error


class TestPitchToFrequency:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        pitch: Any
        a4_frequency: Any
        a4_pitch: Any
        expected_result: Union[float, Type[Exception]]
        test_id: str

    @pytest.mark.parametrize(
        "test_case",
        [
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
                expected_result=8.175798915643707,
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
                expected_result=np.inf,
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
        ],
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

    @pytest.mark.parametrize(
        "test_case",
        [
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
                expected_result=0,
                test_id="zero_frequency",
            ),
            TestCase(
                frequency=-100.0,
                a4_frequency=440.0,
                a4_pitch=69,
                expected_result=0,
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
        ],
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
