from dataclasses import dataclass
from typing import Any, Tuple, Type, Union
from unittest.mock import patch

import numpy as np
import pytest

from sampletones_core.audio.processing import (
    amplitude_to_decibels,
    clip_audio,
    clip_audio_inplace,
    interpolate,
    minmax_decimate,
    normalize,
    quantize,
    resample,
    to_mono,
)
from tests.suite.arrays import assert_array_equal
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.errors import expect_error


class TestAmplitudeToDecibels:
    """Unity is 0 dB, each doubling adds ~6 dB, and silence has no finite level."""

    def test_unity_is_zero_db(self) -> None:
        assert amplitude_to_decibels(1.0) == pytest.approx(0.0)

    def test_doubling_adds_about_six_db(self) -> None:
        assert amplitude_to_decibels(2.0) == pytest.approx(6.0206, abs=1e-4)

    def test_halving_drops_about_six_db(self) -> None:
        assert amplitude_to_decibels(0.5) == pytest.approx(-6.0206, abs=1e-4)

    def test_silence_is_negative_infinity(self) -> None:
        assert amplitude_to_decibels(0.0) == float("-inf")
        assert amplitude_to_decibels(-0.5) == float("-inf")


class TestClipAudio(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[np.ndarray, Type[Exception]]
        audio: Any

    test_cases = (
        TestCase(
            label="within_range",
            audio=np.array([0.5, -0.5, 0.0]),
            expected=np.array([0.5, -0.5, 0.0]),
        ),
        TestCase(
            label="clips_above_and_below",
            audio=np.array([1.5, -1.5, 0.5]),
            expected=np.array(
                [1.0, -1.0, 0.5],
            ),
        ),
        TestCase(
            label="clips_large_values",
            audio=np.array([2.0, -2.0, 3.0]),
            expected=np.array(
                [1.0, -1.0, 1.0],
            ),
        ),
        TestCase(
            label="all_at_max",
            audio=np.array([1.0, 1.0, 1.0]),
            expected=np.array([1.0, 1.0, 1.0]),
        ),
        TestCase(
            label="all_at_min",
            audio=np.array([-1.0, -1.0, -1.0]),
            expected=np.array([-1.0, -1.0, -1.0]),
        ),
        TestCase(label="empty_array", audio=np.array([]), expected=np.array([])),
        TestCase(
            label="float32_dtype",
            audio=np.array([0.5], dtype=np.float32),
            expected=np.array([0.5], dtype=np.float32),
        ),
        TestCase(
            label="int32_clips",
            audio=np.array([10, -10, 5], dtype=np.int32),
            expected=np.array([1, -1, 1], dtype=np.int32),
        ),
        TestCase(
            label="string_raises_type_error",
            audio="not an array",
            expected=TypeError,
        ),
        TestCase(
            label="list_raises_type_error",
            audio=[1.5, -1.5],
            expected=TypeError,
        ),
        TestCase(
            label="none_raises_type_error",
            audio=None,
            expected=TypeError,
        ),
        TestCase(
            label="dict_raises_type_error",
            audio={"audio": [1.0]},
            expected=TypeError,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_clip_audio(self, test_case: TestCase) -> None:
        if expect_error(clip_audio, test_case.expected, test_case.audio):
            return

        result = clip_audio(test_case.audio)
        np.testing.assert_array_equal(result, test_case.expected)


class TestClipAudioInplace(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        audio: np.ndarray
        expected: np.ndarray

    test_cases = (
        TestCase(
            label="clips_above_and_below",
            audio=np.array([1.5, -1.5, 0.5], dtype=np.float32),
            expected=np.array([1.0, -1.0, 0.5], dtype=np.float32),
        ),
        TestCase(
            label="leaves_in_range_untouched",
            audio=np.array([0.25, -0.75, 0.0], dtype=np.float32),
            expected=np.array([0.25, -0.75, 0.0], dtype=np.float32),
        ),
        TestCase(
            label="float64_preserves_dtype",
            audio=np.array([2.0, -3.0], dtype=np.float64),
            expected=np.array([1.0, -1.0], dtype=np.float64),
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_clips_and_preserves_dtype(self, test_case: TestCase) -> None:
        result = clip_audio_inplace(test_case.audio)
        np.testing.assert_array_equal(result, test_case.expected)
        assert result.dtype == test_case.expected.dtype

    def test_returns_the_same_array_object(self) -> None:
        audio = np.array([1.5, -1.5], dtype=np.float32)
        assert clip_audio_inplace(audio) is audio

    def test_mutates_in_place(self) -> None:
        audio = np.array([2.0, -2.0, 0.5], dtype=np.float32)
        clip_audio_inplace(audio)
        np.testing.assert_array_equal(audio, np.array([1.0, -1.0, 0.5], dtype=np.float32))


class TestStereoToMono(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: np.ndarray
        audio: Any

    test_cases = (
        TestCase(
            label="already_mono",
            audio=np.array([1.0, 2.0, 3.0]),
            expected=np.array([1.0, 2.0, 3.0]),
        ),
        TestCase(
            label="stereo",
            audio=np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]),
            expected=np.array([1.5, 3.5, 5.5]),
        ),
        TestCase(
            label="three_channels",
            audio=np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]),
            expected=np.array([2.0, 5.0]),
        ),
        TestCase(
            label="empty_channels",
            audio=np.array([[]]),
            expected=np.array([]),
        ),
        TestCase(
            label="empty_array",
            audio=np.array([]),
            expected=np.array([]),
        ),
        TestCase(
            label="value_array",
            audio=np.array(0.0),
            expected=np.array([0.0]),
        ),
        TestCase(
            label="single_channel_multi",
            audio=np.array([[1.0], [2.0], [3.0]]),
            expected=np.array([1.0, 2.0, 3.0]),
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_mono(self, test_case: TestCase) -> None:
        result = to_mono(test_case.audio)
        np.testing.assert_array_equal(result, test_case.expected)


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


class TestInterpolate(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[np.ndarray, Type[Exception]]
        data: Any
        target_length: Any

    test_cases = (
        TestCase(
            label="same_length",
            data=np.array([1.0, 2.0, 3.0, 4.0]),
            target_length=4,
            expected=np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32),
        ),
        TestCase(
            label="upsample_double",
            data=np.array([1.0, 4.0]),
            target_length=4,
            expected=np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32),
        ),
        TestCase(
            label="downsample_half",
            data=np.array([1.0, 2.0, 3.0, 4.0]),
            target_length=2,
            expected=np.array([1.0, 4.0], dtype=np.float32),
        ),
        TestCase(
            label="downsample_to_one",
            data=np.array([1.0, 2.0, 3.0]),
            target_length=1,
            expected=np.array([1.0], dtype=np.float32),
        ),
        TestCase(
            label="upsample_from_one",
            data=np.array([5.0]),
            target_length=3,
            expected=np.array([5.0, 5.0, 5.0], dtype=np.float32),
        ),
        TestCase(
            label="empty_to_target",
            data=np.array([]),
            target_length=5,
            expected=np.array([], dtype=np.float32),
        ),
        TestCase(
            label="empty_to_zero",
            data=np.array([]),
            target_length=0,
            expected=np.array([], dtype=np.float32),
        ),
        TestCase(
            label="float64_to_float32",
            data=np.array([1.0, 2.0, 3.0], dtype=np.float64),
            target_length=2,
            expected=np.array([1.0, 3.0], dtype=np.float32),
        ),
        TestCase(
            label="int32_to_float32",
            data=np.array([1, 2, 3], dtype=np.int32),
            target_length=2,
            expected=np.array([1.0, 3.0], dtype=np.float32),
        ),
        TestCase(
            label="zero_target_raises_value_error",
            data=np.array([1.0, 2.0, 3.0]),
            target_length=0,
            expected=ValueError,
        ),
        TestCase(
            label="negative_target_raises_value_error",
            data=np.array([1.0, 2.0, 3.0]),
            target_length=-5,
            expected=ValueError,
        ),
        TestCase(
            label="float_target_raises_type_error",
            data=np.array([1.0, 2.0, 3.0]),
            target_length=3.5,
            expected=TypeError,
        ),
        TestCase(
            label="string_target_raises_type_error",
            data=np.array([1.0, 2.0, 3.0]),
            target_length="5",
            expected=TypeError,
        ),
        TestCase(
            label="none_target_raises_type_error",
            data=np.array([1.0, 2.0, 3.0]),
            target_length=None,
            expected=TypeError,
        ),
        TestCase(
            label="string_data_raises_type_error",
            data="not an array",
            target_length=5,
            expected=TypeError,
        ),
        TestCase(
            label="list_data_raises_type_error",
            data=[1.0, 2.0, 3.0],
            target_length=5,
            expected=TypeError,
        ),
        TestCase(
            label="none_data_raises_type_error",
            data=None,
            target_length=5,
            expected=TypeError,
        ),
        TestCase(
            label="2d_data_raises_value_error",
            data=np.array([[1, 2], [3, 4]]),
            target_length=5,
            expected=ValueError,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_interpolate(self, test_case: TestCase) -> None:
        if expect_error(
            interpolate,
            test_case.expected,
            test_case.data,
            test_case.target_length,
        ):
            return

        assert isinstance(test_case.expected, np.ndarray)
        result = interpolate(test_case.data, test_case.target_length)
        np.testing.assert_allclose(result, test_case.expected, rtol=1e-5)


class TestMinmaxDecimate(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[Tuple[np.ndarray, np.ndarray], Type[Exception]]
        data: Any
        num_buckets: Any

    test_cases = (
        TestCase(
            label="divisible_six_elements_three_buckets",
            data=np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]),
            num_buckets=3,
            expected=(
                np.array([0.0, 0.0, 2.0, 2.0, 4.0, 4.0]),
                np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]),
            ),
        ),
        TestCase(
            label="divisible_four_elements_two_buckets",
            data=np.array([-5.0, -2.0, 3.0, 7.0]),
            num_buckets=2,
            expected=(
                np.array([0.0, 0.0, 2.0, 2.0]),
                np.array([-5.0, -2.0, 3.0, 7.0]),
            ),
        ),
        TestCase(
            label="divisible_four_elements_one_bucket",
            data=np.array([1.0, 2.0, 3.0, 4.0]),
            num_buckets=1,
            expected=(np.array([0.0, 0.0]), np.array([1.0, 4.0])),
        ),
        TestCase(
            label="non_divisible_seven_elements_three_buckets",
            data=np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]),
            num_buckets=3,
            expected=(
                np.array([0.0, 0.0, 2.0, 2.0, 4.0, 4.0]),
                np.array([1.0, 2.0, 3.0, 4.0, 5.0, 7.0]),
            ),
        ),
        TestCase(
            label="non_divisible_five_elements_two_buckets",
            data=np.array([10.0, 20.0, 30.0, 40.0, 50.0]),
            num_buckets=2,
            expected=(
                np.array([0.0, 0.0, 2.0, 2.0]),
                np.array([10.0, 20.0, 30.0, 50.0]),
            ),
        ),
        TestCase(
            label="non_divisible_five_elements_two_buckets_negatives",
            data=np.array([-10.0, -5.0, 0.0, 5.0, 10.0]),
            num_buckets=2,
            expected=(
                np.array([0.0, 0.0, 2.0, 2.0]),
                np.array([-10.0, -5.0, 0.0, 10.0]),
            ),
        ),
        TestCase(
            label="non_divisible_five_elements_four_buckets",
            data=np.array([10.0, 20.0, 30.0, 40.0, 50.0]),
            num_buckets=4,
            expected=(
                np.array([0.0, 0.0, 1.0, 1.0, 2.0, 2.0, 3.0, 3.0]),
                np.array([10.0, 10.0, 20.0, 20.0, 30.0, 30.0, 40.0, 50.0]),
            ),
        ),
        TestCase(
            label="non_divisible_ten_elements_seven_buckets",
            data=np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]),
            num_buckets=7,
            expected=(
                np.array(
                    [
                        0.0,
                        0.0,
                        1.0,
                        1.0,
                        2.0,
                        2.0,
                        4.0,
                        4.0,
                        5.0,
                        5.0,
                        7.0,
                        7.0,
                        8.0,
                        8.0,
                    ]
                ),
                np.array(
                    [
                        1.0,
                        1.0,
                        2.0,
                        2.0,
                        3.0,
                        4.0,
                        5.0,
                        5.0,
                        6.0,
                        7.0,
                        8.0,
                        8.0,
                        9.0,
                        10.0,
                    ]
                ),
            ),
        ),
        TestCase(
            label="constant_values_divisible",
            data=np.array([5.0, 5.0, 5.0, 5.0]),
            num_buckets=2,
            expected=(
                np.array([0.0, 0.0, 2.0, 2.0]),
                np.array([5.0, 5.0, 5.0, 5.0]),
            ),
        ),
        TestCase(
            label="single_value_one_bucket",
            data=np.array([1.0]),
            num_buckets=1,
            expected=(np.array([0.0, 0.0]), np.array([1.0, 1.0])),
        ),
        TestCase(
            label="empty_array_zero_case",
            data=np.array([]),
            num_buckets=5,
            expected=(
                np.array([], dtype=np.float32),
                np.array([], dtype=np.float32),
            ),
        ),
        TestCase(
            label="more_buckets_than_samples_non_divisible",
            data=np.array([1.0, 2.0, 3.0]),
            num_buckets=10,
            expected=(
                np.array([0.0, 0.0, 1.0, 1.0, 2.0, 2.0]),
                np.array([1.0, 1.0, 2.0, 2.0, 3.0, 3.0]),
            ),
        ),
        TestCase(
            label="zero_buckets_raises_value_error",
            data=np.array([1.0, 2.0, 3.0]),
            num_buckets=0,
            expected=ValueError,
        ),
        TestCase(
            label="negative_buckets_raises_value_error",
            data=np.array([1.0, 2.0, 3.0]),
            num_buckets=-5,
            expected=ValueError,
        ),
        TestCase(
            label="float_buckets_raises_type_error",
            data=np.array([1.0, 2.0, 3.0]),
            num_buckets=3.5,
            expected=TypeError,
        ),
        TestCase(
            label="string_buckets_raises_type_error",
            data=np.array([1.0, 2.0, 3.0]),
            num_buckets="5",
            expected=TypeError,
        ),
        TestCase(
            label="none_buckets_raises_type_error",
            data=np.array([1.0, 2.0, 3.0]),
            num_buckets=None,
            expected=TypeError,
        ),
        TestCase(
            label="string_data_raises_type_error",
            data="not an array",
            num_buckets=5,
            expected=TypeError,
        ),
        TestCase(
            label="list_data_raises_type_error",
            data=[1.0, 2.0, 3.0],
            num_buckets=5,
            expected=TypeError,
        ),
        TestCase(
            label="none_data_raises_type_error",
            data=None,
            num_buckets=5,
            expected=TypeError,
        ),
        TestCase(
            label="2d_data_raises_value_error",
            data=np.array([[1, 2], [3, 4]]),
            num_buckets=5,
            expected=ValueError,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_minmax_decimate(self, test_case: TestCase) -> None:
        if expect_error(
            minmax_decimate,
            test_case.expected,
            test_case.data,
            num_buckets=test_case.num_buckets,
        ):
            return

        assert isinstance(test_case.expected, tuple)
        x_result, y_result = minmax_decimate(test_case.data, num_buckets=test_case.num_buckets)
        assert_array_equal(x_result, test_case.expected[0])
        assert_array_equal(y_result, test_case.expected[1])


class TestNormalize(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[np.ndarray, Type[Exception]]
        audio: Any

    test_cases = (
        TestCase(
            label="normalize_half_range",
            audio=np.array([0.5, -0.5, 0.25]),
            expected=np.array([1.0, -1.0, 0.5]),
        ),
        TestCase(
            label="normalize_double_range",
            audio=np.array([2.0, -2.0, 1.0]),
            expected=np.array([1.0, -1.0, 0.5]),
        ),
        TestCase(
            label="normalize_small_values",
            audio=np.array([0.1, 0.2, 0.3]),
            expected=np.array([1.0 / 3, 2.0 / 3, 1.0]),
        ),
        TestCase(
            label="already_normalized",
            audio=np.array([1.0, 1.0, 1.0]),
            expected=np.array([1.0, 1.0, 1.0]),
        ),
        TestCase(
            label="all_zeros",
            audio=np.array([0.0, 0.0, 0.0]),
            expected=np.array([0.0, 0.0, 0.0]),
        ),
        TestCase(
            label="empty_array",
            audio=np.array([]),
            expected=np.array([]),
        ),
        TestCase(
            label="nan_replaced_with_zero",
            audio=np.array([np.nan, 1.0, -1.0]),
            expected=np.array([0.0, 1.0, -1.0]),
        ),
        TestCase(
            label="inf_replaced_with_zero",
            audio=np.array([np.inf, 1.0, -1.0]),
            expected=np.array([0.0, 1.0, -1.0]),
        ),
        TestCase(
            label="neginf_replaced_with_zero",
            audio=np.array([-np.inf, 1.0, -1.0]),
            expected=np.array([0.0, 1.0, -1.0]),
        ),
        TestCase(
            label="all_invalid_becomes_zeros",
            audio=np.array([np.nan, np.inf, -np.inf]),
            expected=np.array([0.0, 0.0, 0.0]),
        ),
        TestCase(
            label="float32_dtype",
            audio=np.array([0.5], dtype=np.float32),
            expected=np.array([1.0], dtype=np.float32),
        ),
        TestCase(
            label="int32_normalized",
            audio=np.array([2, -4, 1], dtype=np.int32),
            expected=np.array([0.5, -1.0, 0.25]),
        ),
        TestCase(
            label="string_raises_type_error",
            audio="not an array",
            expected=TypeError,
        ),
        TestCase(
            label="list_raises_type_error",
            audio=[1.0, 2.0, 3.0],
            expected=TypeError,
        ),
        TestCase(
            label="none_raises_type_error",
            audio=None,
            expected=TypeError,
        ),
        TestCase(
            label="2d_raises_value_error",
            audio=np.array([[1, 2], [3, 4]]),
            expected=ValueError,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_normalize(self, test_case: TestCase) -> None:
        if expect_error(normalize, test_case.expected, test_case.audio):
            return

        assert isinstance(test_case.expected, np.ndarray)
        result = normalize(test_case.audio)
        np.testing.assert_allclose(result, test_case.expected, rtol=1e-5)


class TestQuantize(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[np.ndarray, Type[Exception]]
        audio: Any
        levels: Any

    test_cases = (
        TestCase(
            label="three_levels",
            audio=np.array([0.0, 0.6, 1.0, -0.6, -1.0]),
            levels=3,
            expected=np.array([0.0, 1.0, 1.0, -1.0, -1.0]),
        ),
        TestCase(
            label="five_levels",
            audio=np.array([0.0, 0.3, 0.6, 0.8, 1.0]),
            levels=5,
            expected=np.array([0.0, 0.5, 0.5, 1.0, 1.0]),
        ),
        TestCase(
            label="seven_levels",
            audio=np.array([0.1, 0.2, 0.4]),
            levels=7,
            expected=np.array([0.0, 1.0 / 3, 1.0 / 3]),
        ),
        TestCase(
            label="single_value",
            audio=np.array([0.0]),
            levels=3,
            expected=np.array([0.0]),
        ),
        TestCase(
            label="empty_array",
            audio=np.array([]),
            levels=3,
            expected=np.array([]),
        ),
        TestCase(
            label="even_adjusted_to_odd",
            audio=np.array([0.6, -0.6]),
            levels=4,
            expected=np.array([1.0, -1.0]),
        ),
        TestCase(
            label="float32_dtype",
            audio=np.array([0.6, -0.6], dtype=np.float32),
            levels=3,
            expected=np.array([1.0, -1.0], dtype=np.float32),
        ),
        TestCase(
            label="two_levels_raises_value_error",
            audio=np.array([0.5, -0.5]),
            levels=2,
            expected=ValueError,
        ),
        TestCase(
            label="one_level_raises_value_error",
            audio=np.array([0.5, -0.5]),
            levels=1,
            expected=ValueError,
        ),
        TestCase(
            label="zero_levels_raises_value_error",
            audio=np.array([0.5, -0.5]),
            levels=0,
            expected=ValueError,
        ),
        TestCase(
            label="negative_levels_raises_value_error",
            audio=np.array([0.5, -0.5]),
            levels=-5,
            expected=ValueError,
        ),
        TestCase(
            label="float_levels_raises_type_error",
            audio=np.array([0.5, -0.5]),
            levels=3.5,
            expected=TypeError,
        ),
        TestCase(
            label="string_levels_raises_type_error",
            audio=np.array([0.5, -0.5]),
            levels="3",
            expected=TypeError,
        ),
        TestCase(
            label="none_levels_raises_type_error",
            audio=np.array([0.5, -0.5]),
            levels=None,
            expected=TypeError,
        ),
        TestCase(
            label="string_audio_raises_type_error",
            audio="not an array",
            levels=3,
            expected=TypeError,
        ),
        TestCase(
            label="list_audio_raises_type_error",
            audio=[0.5, -0.5],
            levels=3,
            expected=TypeError,
        ),
        TestCase(
            label="none_audio_raises_type_error",
            audio=None,
            levels=3,
            expected=TypeError,
        ),
        TestCase(
            label="2d_audio_raises_value_error",
            audio=np.array([[1, 2], [3, 4]]),
            levels=3,
            expected=ValueError,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_quantize(self, test_case: TestCase) -> None:
        if expect_error(
            quantize,
            test_case.expected,
            test_case.audio,
            levels=test_case.levels,
        ):
            return

        assert isinstance(test_case.expected, np.ndarray)
        result = quantize(test_case.audio, levels=test_case.levels)
        np.testing.assert_allclose(result, test_case.expected, rtol=1e-5)
