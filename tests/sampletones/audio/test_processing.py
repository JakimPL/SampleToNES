from dataclasses import dataclass
from typing import Any, Tuple, Type, Union
from unittest.mock import patch

import numpy as np
import pytest

from sampletones.audio.processing import (
    clip_audio,
    interpolate,
    minmax_decimate,
    normalize,
    quantize,
    resample,
    to_mono,
)
from tests.sampletones.arrays import assert_array_equal
from tests.sampletones.errors import expect_error


class TestClipAudio:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        audio: Any
        expected_result: Union[np.ndarray, Type[Exception]]

    test_cases = [
        TestCase(
            test_id="within_range",
            audio=np.array([0.5, -0.5, 0.0]),
            expected_result=np.array([0.5, -0.5, 0.0]),
        ),
        TestCase(
            test_id="clips_above_and_below",
            audio=np.array([1.5, -1.5, 0.5]),
            expected_result=np.array(
                [1.0, -1.0, 0.5],
            ),
        ),
        TestCase(
            test_id="clips_large_values",
            audio=np.array([2.0, -2.0, 3.0]),
            expected_result=np.array(
                [1.0, -1.0, 1.0],
            ),
        ),
        TestCase(
            test_id="all_at_max",
            audio=np.array([1.0, 1.0, 1.0]),
            expected_result=np.array([1.0, 1.0, 1.0]),
        ),
        TestCase(
            test_id="all_at_min",
            audio=np.array([-1.0, -1.0, -1.0]),
            expected_result=np.array([-1.0, -1.0, -1.0]),
        ),
        TestCase(test_id="empty_array", audio=np.array([]), expected_result=np.array([])),
        TestCase(
            test_id="float32_dtype",
            audio=np.array([0.5], dtype=np.float32),
            expected_result=np.array([0.5], dtype=np.float32),
        ),
        TestCase(
            test_id="int32_clips",
            audio=np.array([10, -10, 5], dtype=np.int32),
            expected_result=np.array([1, -1, 1], dtype=np.int32),
        ),
        TestCase(
            test_id="string_raises_type_error",
            audio="not an array",
            expected_result=TypeError,
        ),
        TestCase(
            test_id="list_raises_type_error",
            audio=[1.5, -1.5],
            expected_result=TypeError,
        ),
        TestCase(
            test_id="none_raises_type_error",
            audio=None,
            expected_result=TypeError,
        ),
        TestCase(
            test_id="dict_raises_type_error",
            audio={"audio": [1.0]},
            expected_result=TypeError,
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_clip_audio(self, test_case: TestCase) -> None:
        if expect_error(clip_audio, test_case.expected_result, test_case.audio):
            return

        result = clip_audio(test_case.audio)
        np.testing.assert_array_equal(result, test_case.expected_result)


class TestStereoToMono:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        audio: Any
        expected_result: np.ndarray

    test_cases = [
        TestCase(test_id="already_mono", audio=np.array([1.0, 2.0, 3.0]), expected_result=np.array([1.0, 2.0, 3.0])),
        TestCase(
            test_id="stereo",
            audio=np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]),
            expected_result=np.array([1.5, 3.5, 5.5]),
        ),
        TestCase(
            test_id="three_channels",
            audio=np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]),
            expected_result=np.array([2.0, 5.0]),
        ),
        TestCase(
            test_id="empty_channels",
            audio=np.array([[]]),
            expected_result=np.array([]),
        ),
        TestCase(
            test_id="empty_array",
            audio=np.array([]),
            expected_result=np.array([]),
        ),
        TestCase(
            test_id="value_array",
            audio=np.array(0.0),
            expected_result=np.array([0.0]),
        ),
        TestCase(
            test_id="single_channel_multi",
            audio=np.array([[1.0], [2.0], [3.0]]),
            expected_result=np.array([1.0, 2.0, 3.0]),
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_mono(self, test_case: TestCase) -> None:
        result = to_mono(test_case.audio)
        np.testing.assert_array_equal(result, test_case.expected_result)


class TestResample:
    def test_resample(self) -> None:
        array = np.array([2.0, 3.0], dtype=np.float32)
        resampled = np.array([2.0426471, 3.1752715, 2.9565508, 1.4901037], dtype=np.float32)
        sample_rate = 22050
        target_sample_rate = 44100
        with patch("librosa.resample", return_value=resampled) as mock_resample:
            resample(array, sample_rate, target_sample_rate)
            mock_resample.assert_called_once_with(
                array,
                orig_sr=sample_rate,
                target_sr=target_sample_rate,
            )

    def test_resample_identical(self) -> None:
        array = np.array([2.0, 3.0], dtype=np.float32)
        sample_rate = 22050
        target_sample_rate = 22050
        with patch("librosa.resample", return_value=array) as mock_resample:
            resample(array, sample_rate, target_sample_rate)
            mock_resample.assert_not_called()


class TestInterpolate:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        data: Any
        target_length: Any
        expected_result: Union[np.ndarray, Type[Exception]]

    test_cases = [
        TestCase(
            test_id="same_length",
            data=np.array([1.0, 2.0, 3.0, 4.0]),
            target_length=4,
            expected_result=np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32),
        ),
        TestCase(
            test_id="upsample_double",
            data=np.array([1.0, 4.0]),
            target_length=4,
            expected_result=np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32),
        ),
        TestCase(
            test_id="downsample_half",
            data=np.array([1.0, 2.0, 3.0, 4.0]),
            target_length=2,
            expected_result=np.array([1.0, 4.0], dtype=np.float32),
        ),
        TestCase(
            test_id="downsample_to_one",
            data=np.array([1.0, 2.0, 3.0]),
            target_length=1,
            expected_result=np.array([1.0], dtype=np.float32),
        ),
        TestCase(
            test_id="upsample_from_one",
            data=np.array([5.0]),
            target_length=3,
            expected_result=np.array([5.0, 5.0, 5.0], dtype=np.float32),
        ),
        TestCase(
            test_id="empty_to_target",
            data=np.array([]),
            target_length=5,
            expected_result=np.array([], dtype=np.float32),
        ),
        TestCase(
            test_id="empty_to_zero",
            data=np.array([]),
            target_length=0,
            expected_result=np.array([], dtype=np.float32),
        ),
        TestCase(
            test_id="float64_to_float32",
            data=np.array([1.0, 2.0, 3.0], dtype=np.float64),
            target_length=2,
            expected_result=np.array([1.0, 3.0], dtype=np.float32),
        ),
        TestCase(
            test_id="int32_to_float32",
            data=np.array([1, 2, 3], dtype=np.int32),
            target_length=2,
            expected_result=np.array([1.0, 3.0], dtype=np.float32),
        ),
        TestCase(
            test_id="zero_target_raises_value_error",
            data=np.array([1.0, 2.0, 3.0]),
            target_length=0,
            expected_result=ValueError,
        ),
        TestCase(
            test_id="negative_target_raises_value_error",
            data=np.array([1.0, 2.0, 3.0]),
            target_length=-5,
            expected_result=ValueError,
        ),
        TestCase(
            test_id="float_target_raises_type_error",
            data=np.array([1.0, 2.0, 3.0]),
            target_length=3.5,
            expected_result=TypeError,
        ),
        TestCase(
            test_id="string_target_raises_type_error",
            data=np.array([1.0, 2.0, 3.0]),
            target_length="5",
            expected_result=TypeError,
        ),
        TestCase(
            test_id="none_target_raises_type_error",
            data=np.array([1.0, 2.0, 3.0]),
            target_length=None,
            expected_result=TypeError,
        ),
        TestCase(
            test_id="string_data_raises_type_error",
            data="not an array",
            target_length=5,
            expected_result=TypeError,
        ),
        TestCase(
            test_id="list_data_raises_type_error",
            data=[1.0, 2.0, 3.0],
            target_length=5,
            expected_result=TypeError,
        ),
        TestCase(
            test_id="none_data_raises_type_error",
            data=None,
            target_length=5,
            expected_result=TypeError,
        ),
        TestCase(
            test_id="2d_data_raises_value_error",
            data=np.array([[1, 2], [3, 4]]),
            target_length=5,
            expected_result=ValueError,
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_interpolate(self, test_case: TestCase) -> None:
        if expect_error(interpolate, test_case.expected_result, test_case.data, test_case.target_length):
            return

        assert isinstance(test_case.expected_result, np.ndarray)
        result = interpolate(test_case.data, test_case.target_length)
        np.testing.assert_allclose(result, test_case.expected_result, rtol=1e-5)


class TestMinmaxDecimate:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        data: Any
        num_buckets: Any
        expected_result: Union[Tuple[np.ndarray, np.ndarray], Type[Exception]]

    test_cases = [
        TestCase(
            test_id="divisible_six_elements_three_buckets",
            data=np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]),
            num_buckets=3,
            expected_result=(np.array([1.0, 1.0, 3.0, 3.0, 5.0, 5.0]), np.array([2.0, 1.5, 4.0, 3.5, 6.0, 5.5])),
        ),
        TestCase(
            test_id="divisible_four_elements_two_buckets",
            data=np.array([-5.0, -2.0, 3.0, 7.0]),
            num_buckets=2,
            expected_result=(np.array([-5.0, -5.0, 3.0, 3.0]), np.array([-2.0, -3.5, 7.0, 5.0])),
        ),
        TestCase(
            test_id="divisible_four_elements_one_bucket",
            data=np.array([1.0, 2.0, 3.0, 4.0]),
            num_buckets=1,
            expected_result=(np.array([1.0, 1.0]), np.array([4.0, 2.5])),
        ),
        TestCase(
            test_id="non_divisible_seven_elements_three_buckets",
            data=np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]),
            num_buckets=3,
            expected_result=(np.array([1.0, 1.0, 4.0, 4.0, 7.0, 7.0]), np.array([3.0, 2.0, 6.0, 5.0, 7.0, 7.0])),
        ),
        TestCase(
            test_id="non_divisible_five_elements_two_buckets",
            data=np.array([10.0, 20.0, 30.0, 40.0, 50.0]),
            num_buckets=2,
            expected_result=(np.array([10.0, 10.0, 40.0, 40.0]), np.array([30.0, 20.0, 50.0, 45.0])),
        ),
        TestCase(
            test_id="non_divisible_five_elements_two_buckets_negatives",
            data=np.array([-10.0, -5.0, 0.0, 5.0, 10.0]),
            num_buckets=2,
            expected_result=(np.array([-10.0, -10.0, 5.0, 5.0]), np.array([0.0, -5.0, 10.0, 7.5])),
        ),
        TestCase(
            test_id="constant_values_divisible",
            data=np.array([5.0, 5.0, 5.0, 5.0]),
            num_buckets=2,
            expected_result=(np.array([5.0, 5.0, 5.0, 5.0]), np.array([5.0, 5.0, 5.0, 5.0])),
        ),
        TestCase(
            test_id="single_value_one_bucket",
            data=np.array([1.0]),
            num_buckets=1,
            expected_result=(np.array([1.0, 1.0]), np.array([1.0, 1.0])),
        ),
        TestCase(
            test_id="empty_array_zero_case",
            data=np.array([]),
            num_buckets=5,
            expected_result=(np.array([], dtype=np.float32), np.array([], dtype=np.float32)),
        ),
        TestCase(
            test_id="more_buckets_than_samples_non_divisible",
            data=np.array([1.0, 2.0, 3.0]),
            num_buckets=10,
            expected_result=(
                np.array([1.0, 1.0, 2.0, 2.0, 3.0, 3.0]),
                np.array([1.0, 1.0, 2.0, 2.0, 3.0, 3.0]),
            ),
        ),
        TestCase(
            test_id="zero_buckets_raises_value_error",
            data=np.array([1.0, 2.0, 3.0]),
            num_buckets=0,
            expected_result=ValueError,
        ),
        TestCase(
            test_id="negative_buckets_raises_value_error",
            data=np.array([1.0, 2.0, 3.0]),
            num_buckets=-5,
            expected_result=ValueError,
        ),
        TestCase(
            test_id="float_buckets_raises_type_error",
            data=np.array([1.0, 2.0, 3.0]),
            num_buckets=3.5,
            expected_result=TypeError,
        ),
        TestCase(
            test_id="string_buckets_raises_type_error",
            data=np.array([1.0, 2.0, 3.0]),
            num_buckets="5",
            expected_result=TypeError,
        ),
        TestCase(
            test_id="none_buckets_raises_type_error",
            data=np.array([1.0, 2.0, 3.0]),
            num_buckets=None,
            expected_result=TypeError,
        ),
        TestCase(
            test_id="string_data_raises_type_error",
            data="not an array",
            num_buckets=5,
            expected_result=TypeError,
        ),
        TestCase(
            test_id="list_data_raises_type_error",
            data=[1.0, 2.0, 3.0],
            num_buckets=5,
            expected_result=TypeError,
        ),
        TestCase(
            test_id="none_data_raises_type_error",
            data=None,
            num_buckets=5,
            expected_result=TypeError,
        ),
        TestCase(
            test_id="2d_data_raises_value_error",
            data=np.array([[1, 2], [3, 4]]),
            num_buckets=5,
            expected_result=ValueError,
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_minmax_decimate(self, test_case: TestCase) -> None:
        if expect_error(minmax_decimate, test_case.expected_result, test_case.data, test_case.num_buckets):
            return

        assert isinstance(test_case.expected_result, tuple)
        x_result, y_result = minmax_decimate(test_case.data, test_case.num_buckets)
        assert_array_equal(x_result, test_case.expected_result[0])
        assert_array_equal(y_result, test_case.expected_result[1])


class TestNormalize:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        audio: Any
        expected_result: Union[np.ndarray, Type[Exception]]

    test_cases = [
        TestCase(
            test_id="normalize_half_range",
            audio=np.array([0.5, -0.5, 0.25]),
            expected_result=np.array([1.0, -1.0, 0.5]),
        ),
        TestCase(
            test_id="normalize_double_range",
            audio=np.array([2.0, -2.0, 1.0]),
            expected_result=np.array([1.0, -1.0, 0.5]),
        ),
        TestCase(
            test_id="normalize_small_values",
            audio=np.array([0.1, 0.2, 0.3]),
            expected_result=np.array([1.0 / 3, 2.0 / 3, 1.0]),
        ),
        TestCase(
            test_id="already_normalized",
            audio=np.array([1.0, 1.0, 1.0]),
            expected_result=np.array([1.0, 1.0, 1.0]),
        ),
        TestCase(
            test_id="all_zeros",
            audio=np.array([0.0, 0.0, 0.0]),
            expected_result=np.array([0.0, 0.0, 0.0]),
        ),
        TestCase(
            test_id="empty_array",
            audio=np.array([]),
            expected_result=np.array([]),
        ),
        TestCase(
            test_id="nan_replaced_with_zero",
            audio=np.array([np.nan, 1.0, -1.0]),
            expected_result=np.array([0.0, 1.0, -1.0]),
        ),
        TestCase(
            test_id="inf_replaced_with_zero",
            audio=np.array([np.inf, 1.0, -1.0]),
            expected_result=np.array([0.0, 1.0, -1.0]),
        ),
        TestCase(
            test_id="neginf_replaced_with_zero",
            audio=np.array([-np.inf, 1.0, -1.0]),
            expected_result=np.array([0.0, 1.0, -1.0]),
        ),
        TestCase(
            test_id="all_invalid_becomes_zeros",
            audio=np.array([np.nan, np.inf, -np.inf]),
            expected_result=np.array([0.0, 0.0, 0.0]),
        ),
        TestCase(
            test_id="float32_dtype",
            audio=np.array([0.5], dtype=np.float32),
            expected_result=np.array([1.0], dtype=np.float32),
        ),
        TestCase(
            test_id="int32_normalized",
            audio=np.array([2, -4, 1], dtype=np.int32),
            expected_result=np.array([0.5, -1.0, 0.25]),
        ),
        TestCase(
            test_id="string_raises_type_error",
            audio="not an array",
            expected_result=TypeError,
        ),
        TestCase(
            test_id="list_raises_type_error",
            audio=[1.0, 2.0, 3.0],
            expected_result=TypeError,
        ),
        TestCase(
            test_id="none_raises_type_error",
            audio=None,
            expected_result=TypeError,
        ),
        TestCase(
            test_id="2d_raises_value_error",
            audio=np.array([[1, 2], [3, 4]]),
            expected_result=ValueError,
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_normalize(self, test_case: TestCase) -> None:
        if expect_error(normalize, test_case.expected_result, test_case.audio):
            return

        assert isinstance(test_case.expected_result, np.ndarray)
        result = normalize(test_case.audio)
        np.testing.assert_allclose(result, test_case.expected_result, rtol=1e-5)


class TestQuantize:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        audio: Any
        levels: Any
        expected_result: Union[np.ndarray, Type[Exception]]

    test_cases = [
        TestCase(
            test_id="three_levels",
            audio=np.array([0.0, 0.6, 1.0, -0.6, -1.0]),
            levels=3,
            expected_result=np.array([0.0, 1.0, 1.0, -1.0, -1.0]),
        ),
        TestCase(
            test_id="five_levels",
            audio=np.array([0.0, 0.3, 0.6, 0.8, 1.0]),
            levels=5,
            expected_result=np.array([0.0, 0.5, 0.5, 1.0, 1.0]),
        ),
        TestCase(
            test_id="seven_levels",
            audio=np.array([0.1, 0.2, 0.4]),
            levels=7,
            expected_result=np.array([0.0, 1.0 / 3, 1.0 / 3]),
        ),
        TestCase(
            test_id="single_value",
            audio=np.array([0.0]),
            levels=3,
            expected_result=np.array([0.0]),
        ),
        TestCase(
            test_id="empty_array",
            audio=np.array([]),
            levels=3,
            expected_result=np.array([]),
        ),
        TestCase(
            test_id="even_adjusted_to_odd",
            audio=np.array([0.6, -0.6]),
            levels=4,
            expected_result=np.array([1.0, -1.0]),
        ),
        TestCase(
            test_id="float32_dtype",
            audio=np.array([0.6, -0.6], dtype=np.float32),
            levels=3,
            expected_result=np.array([1.0, -1.0], dtype=np.float32),
        ),
        TestCase(
            test_id="two_levels_raises_value_error",
            audio=np.array([0.5, -0.5]),
            levels=2,
            expected_result=ValueError,
        ),
        TestCase(
            test_id="one_level_raises_value_error",
            audio=np.array([0.5, -0.5]),
            levels=1,
            expected_result=ValueError,
        ),
        TestCase(
            test_id="zero_levels_raises_value_error",
            audio=np.array([0.5, -0.5]),
            levels=0,
            expected_result=ValueError,
        ),
        TestCase(
            test_id="negative_levels_raises_value_error",
            audio=np.array([0.5, -0.5]),
            levels=-5,
            expected_result=ValueError,
        ),
        TestCase(
            test_id="float_levels_raises_type_error",
            audio=np.array([0.5, -0.5]),
            levels=3.5,
            expected_result=TypeError,
        ),
        TestCase(
            test_id="string_levels_raises_type_error",
            audio=np.array([0.5, -0.5]),
            levels="3",
            expected_result=TypeError,
        ),
        TestCase(
            test_id="none_levels_raises_type_error",
            audio=np.array([0.5, -0.5]),
            levels=None,
            expected_result=TypeError,
        ),
        TestCase(
            test_id="string_audio_raises_type_error",
            audio="not an array",
            levels=3,
            expected_result=TypeError,
        ),
        TestCase(
            test_id="list_audio_raises_type_error",
            audio=[0.5, -0.5],
            levels=3,
            expected_result=TypeError,
        ),
        TestCase(
            test_id="none_audio_raises_type_error",
            audio=None,
            levels=3,
            expected_result=TypeError,
        ),
        TestCase(
            test_id="2d_audio_raises_value_error",
            audio=np.array([[1, 2], [3, 4]]),
            levels=3,
            expected_result=ValueError,
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_quantize(self, test_case: TestCase) -> None:
        if expect_error(quantize, test_case.expected_result, test_case.audio, test_case.levels):
            return

        assert isinstance(test_case.expected_result, np.ndarray)
        result = quantize(test_case.audio, test_case.levels)
        np.testing.assert_allclose(result, test_case.expected_result, rtol=1e-5)
