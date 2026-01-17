import sys
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
    validate_audio_array,
)
from tests.sampletones.errors import expect_error


class TestValidateAudioArray:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        id: str
        audio: Any
        expected_result: Union[None, Type[Exception]]

    @pytest.mark.parametrize(
        "test_case",
        [
            TestCase(id="valid_float64_array", audio=np.array([1.0, 2.0, 3.0]), expected_result=None),
            TestCase(id="empty_array", audio=np.array([]), expected_result=None),
            TestCase(id="valid_float32_array", audio=np.array([1.0, 2.0, 3.0], dtype=np.float32), expected_result=None),
            TestCase(id="valid_int32_array", audio=np.array([1, 2, 3], dtype=np.int32), expected_result=None),
            TestCase(id="string_raises_type_error", audio="not an array", expected_result=TypeError),
            TestCase(id="list_raises_type_error", audio=[1.0, 2.0, 3.0], expected_result=TypeError),
            TestCase(id="none_raises_type_error", audio=None, expected_result=TypeError),
            TestCase(id="int_raises_type_error", audio=123, expected_result=TypeError),
            TestCase(id="2d_array_raises_value_error", audio=np.array([[1, 2], [3, 4]]), expected_result=ValueError),
            TestCase(id="3d_array_raises_value_error", audio=np.array([[[1]]]), expected_result=ValueError),
        ],
        ids=lambda tc: tc.id,
    )
    def test_validate_audio_array(self, test_case: TestCase) -> None:
        if expect_error(validate_audio_array, test_case.expected_result, test_case.audio):
            return

        validate_audio_array(test_case.audio)


class TestClipAudio:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        id: str
        audio: Any
        expected_result: Union[np.ndarray, Type[Exception]]

    @pytest.mark.parametrize(
        "test_case",
        [
            TestCase(id="within_range", audio=np.array([0.5, -0.5, 0.0]), expected_result=np.array([0.5, -0.5, 0.0])),
            TestCase(
                id="clips_above_and_below", audio=np.array([1.5, -1.5, 0.5]), expected_result=np.array([1.0, -1.0, 0.5])
            ),
            TestCase(
                id="clips_large_values", audio=np.array([2.0, -2.0, 3.0]), expected_result=np.array([1.0, -1.0, 1.0])
            ),
            TestCase(id="all_at_max", audio=np.array([1.0, 1.0, 1.0]), expected_result=np.array([1.0, 1.0, 1.0])),
            TestCase(id="all_at_min", audio=np.array([-1.0, -1.0, -1.0]), expected_result=np.array([-1.0, -1.0, -1.0])),
            TestCase(id="empty_array", audio=np.array([]), expected_result=np.array([])),
            TestCase(
                id="float32_dtype",
                audio=np.array([0.5], dtype=np.float32),
                expected_result=np.array([0.5], dtype=np.float32),
            ),
            TestCase(
                id="int32_clips",
                audio=np.array([10, -10, 5], dtype=np.int32),
                expected_result=np.array([1, -1, 1], dtype=np.int32),
            ),
            TestCase(id="string_raises_type_error", audio="not an array", expected_result=TypeError),
            TestCase(id="list_raises_type_error", audio=[1.5, -1.5], expected_result=TypeError),
            TestCase(id="none_raises_type_error", audio=None, expected_result=TypeError),
            TestCase(id="dict_raises_type_error", audio={"audio": [1.0]}, expected_result=TypeError),
        ],
        ids=lambda tc: tc.id,
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

        id: str
        audio: Any
        expected_result: np.ndarray

    @pytest.mark.parametrize(
        "test_case",
        [
            TestCase(id="already_mono", audio=np.array([1.0, 2.0, 3.0]), expected_result=np.array([1.0, 2.0, 3.0])),
            TestCase(
                id="stereo",
                audio=np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]),
                expected_result=np.array([1.5, 3.5, 5.5]),
            ),
            TestCase(
                id="three_channels",
                audio=np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]),
                expected_result=np.array([2.0, 5.0]),
            ),
            TestCase(id="empty_channels", audio=np.array([[]]), expected_result=np.array([])),
            TestCase(id="empty_array", audio=np.array([]), expected_result=np.array([])),
            TestCase(id="value_array", audio=np.array(0.0), expected_result=np.array([0.0])),
            TestCase(
                id="single_channel_multi",
                audio=np.array([[1.0], [2.0], [3.0]]),
                expected_result=np.array([1.0, 2.0, 3.0]),
            ),
        ],
        ids=lambda tc: tc.id,
    )
    def test_mono(self, test_case: TestCase) -> None:
        result = to_mono(test_case.audio)
        np.testing.assert_array_equal(result, test_case.expected_result)


class TestResample:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        id: str
        audio: np.ndarray
        original_sample_rate: int
        target_sample_rate: int
        expected_result: Union[np.ndarray, int]
        use_librosa: bool

    @pytest.mark.parametrize(
        "test_case",
        [
            TestCase(
                id="same_rate_no_change",
                audio=np.array([1.0, 2.0, 3.0, 4.0]),
                original_sample_rate=44100,
                target_sample_rate=44100,
                expected_result=np.array([1.0, 2.0, 3.0, 4.0]),
                use_librosa=False,
            ),
            TestCase(
                id="downsample_half",
                audio=np.array([1.0, 4.0]),
                original_sample_rate=44100,
                target_sample_rate=22050,
                expected_result=np.array([1.0]),
                use_librosa=False,
            ),
            TestCase(
                id="upsample_double",
                audio=np.array([1.0, 3.0]),
                original_sample_rate=22050,
                target_sample_rate=44100,
                expected_result=np.array([1.0, 1.66666667, 2.33333333, 3.0]),
                use_librosa=False,
            ),
            TestCase(
                id="empty_array",
                audio=np.array([]),
                original_sample_rate=44100,
                target_sample_rate=22050,
                expected_result=np.array([]),
                use_librosa=False,
            ),
            TestCase(
                id="librosa_called_with_correct_params",
                audio=np.array([1.0, 2.0, 3.0, 4.0]),
                original_sample_rate=48000,
                target_sample_rate=44100,
                expected_result=0,
                use_librosa=True,
            ),
        ],
        ids=lambda tc: tc.id,
    )
    def test_resample(self, test_case: TestCase) -> None:
        if test_case.use_librosa:
            with patch("librosa.resample") as mock_resample:
                mock_resample.return_value = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)
                resample(test_case.audio, test_case.original_sample_rate, test_case.target_sample_rate)
                mock_resample.assert_called_once_with(
                    test_case.audio, orig_sr=test_case.original_sample_rate, target_sr=test_case.target_sample_rate
                )
        else:
            with patch.dict(sys.modules, {"librosa": None}):
                result = resample(test_case.audio, test_case.original_sample_rate, test_case.target_sample_rate)
                np.testing.assert_allclose(result, test_case.expected_result, rtol=1e-5)


class TestInterpolate:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        id: str
        data: Any
        target_length: Any
        expected_result: Union[np.ndarray, Type[Exception]]

    @pytest.mark.parametrize(
        "test_case",
        [
            TestCase(
                id="same_length",
                data=np.array([1.0, 2.0, 3.0, 4.0]),
                target_length=4,
                expected_result=np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32),
            ),
            TestCase(
                id="upsample_double",
                data=np.array([1.0, 4.0]),
                target_length=4,
                expected_result=np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32),
            ),
            TestCase(
                id="downsample_half",
                data=np.array([1.0, 2.0, 3.0, 4.0]),
                target_length=2,
                expected_result=np.array([1.0, 4.0], dtype=np.float32),
            ),
            TestCase(
                id="downsample_to_one",
                data=np.array([1.0, 2.0, 3.0]),
                target_length=1,
                expected_result=np.array([1.0], dtype=np.float32),
            ),
            TestCase(
                id="upsample_from_one",
                data=np.array([5.0]),
                target_length=3,
                expected_result=np.array([5.0, 5.0, 5.0], dtype=np.float32),
            ),
            TestCase(
                id="empty_to_target", data=np.array([]), target_length=5, expected_result=np.array([], dtype=np.float32)
            ),
            TestCase(
                id="empty_to_zero", data=np.array([]), target_length=0, expected_result=np.array([], dtype=np.float32)
            ),
            TestCase(
                id="float64_to_float32",
                data=np.array([1.0, 2.0, 3.0], dtype=np.float64),
                target_length=2,
                expected_result=np.array([1.0, 3.0], dtype=np.float32),
            ),
            TestCase(
                id="int32_to_float32",
                data=np.array([1, 2, 3], dtype=np.int32),
                target_length=2,
                expected_result=np.array([1.0, 3.0], dtype=np.float32),
            ),
            TestCase(
                id="zero_target_raises_value_error",
                data=np.array([1.0, 2.0, 3.0]),
                target_length=0,
                expected_result=ValueError,
            ),
            TestCase(
                id="negative_target_raises_value_error",
                data=np.array([1.0, 2.0, 3.0]),
                target_length=-5,
                expected_result=ValueError,
            ),
            TestCase(
                id="float_target_raises_type_error",
                data=np.array([1.0, 2.0, 3.0]),
                target_length=3.5,
                expected_result=TypeError,
            ),
            TestCase(
                id="string_target_raises_type_error",
                data=np.array([1.0, 2.0, 3.0]),
                target_length="5",
                expected_result=TypeError,
            ),
            TestCase(
                id="none_target_raises_type_error",
                data=np.array([1.0, 2.0, 3.0]),
                target_length=None,
                expected_result=TypeError,
            ),
            TestCase(
                id="string_data_raises_type_error", data="not an array", target_length=5, expected_result=TypeError
            ),
            TestCase(
                id="list_data_raises_type_error", data=[1.0, 2.0, 3.0], target_length=5, expected_result=TypeError
            ),
            TestCase(id="none_data_raises_type_error", data=None, target_length=5, expected_result=TypeError),
            TestCase(
                id="2d_data_raises_value_error",
                data=np.array([[1, 2], [3, 4]]),
                target_length=5,
                expected_result=ValueError,
            ),
        ],
        ids=lambda tc: tc.id,
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

        id: str
        data: Any
        num_buckets: Any
        expected_result: Union[Tuple[np.ndarray, np.ndarray], Type[Exception]]

    @pytest.mark.parametrize(
        "test_case",
        [
            TestCase(
                id="three_buckets",
                data=np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]),
                num_buckets=3,
                expected_result=(np.array([1.0, 1.0, 3.0, 3.0, 5.0, 5.0]), np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])),
            ),
            TestCase(
                id="two_buckets_with_negatives",
                data=np.array([1.0, -1.0, 2.0, -2.0]),
                num_buckets=2,
                expected_result=(np.array([1.0, 1.0, 3.0, 3.0]), np.array([-1.0, 1.0, -2.0, 2.0])),
            ),
            TestCase(
                id="constant_values",
                data=np.array([5.0, 5.0, 5.0, 5.0]),
                num_buckets=2,
                expected_result=(np.array([1.0, 1.0, 3.0, 3.0]), np.array([5.0, 5.0, 5.0, 5.0])),
            ),
            TestCase(
                id="single_value",
                data=np.array([1.0]),
                num_buckets=1,
                expected_result=(np.array([0.5, 0.5]), np.array([1.0, 1.0])),
            ),
            TestCase(
                id="empty_array",
                data=np.array([]),
                num_buckets=5,
                expected_result=(np.array([], dtype=np.float32), np.array([], dtype=np.float32)),
            ),
            TestCase(
                id="more_buckets_than_samples",
                data=np.array([1.0, 2.0, 3.0]),
                num_buckets=10,
                expected_result=(np.array([0.5, 0.5, 1.5, 1.5, 2.5, 2.5]), np.array([1.0, 1.0, 2.0, 2.0, 3.0, 3.0])),
            ),
            TestCase(
                id="zero_buckets_raises_value_error",
                data=np.array([1.0, 2.0, 3.0]),
                num_buckets=0,
                expected_result=ValueError,
            ),
            TestCase(
                id="negative_buckets_raises_value_error",
                data=np.array([1.0, 2.0, 3.0]),
                num_buckets=-5,
                expected_result=ValueError,
            ),
            TestCase(
                id="float_buckets_raises_type_error",
                data=np.array([1.0, 2.0, 3.0]),
                num_buckets=3.5,
                expected_result=TypeError,
            ),
            TestCase(
                id="string_buckets_raises_type_error",
                data=np.array([1.0, 2.0, 3.0]),
                num_buckets="5",
                expected_result=TypeError,
            ),
            TestCase(
                id="none_buckets_raises_type_error",
                data=np.array([1.0, 2.0, 3.0]),
                num_buckets=None,
                expected_result=TypeError,
            ),
            TestCase(id="string_data_raises_type_error", data="not an array", num_buckets=5, expected_result=TypeError),
            TestCase(id="list_data_raises_type_error", data=[1.0, 2.0, 3.0], num_buckets=5, expected_result=TypeError),
            TestCase(id="none_data_raises_type_error", data=None, num_buckets=5, expected_result=TypeError),
            TestCase(
                id="2d_data_raises_value_error",
                data=np.array([[1, 2], [3, 4]]),
                num_buckets=5,
                expected_result=ValueError,
            ),
        ],
        ids=lambda tc: tc.id,
    )
    def test_minmax_decimate(self, test_case: TestCase) -> None:
        if expect_error(minmax_decimate, test_case.expected_result, test_case.data, test_case.num_buckets):
            return

        assert isinstance(test_case.expected_result, tuple)
        x_result, y_result = minmax_decimate(test_case.data, test_case.num_buckets)
        if isinstance(test_case.expected_result[0], np.ndarray) and test_case.expected_result[0].size == 0:
            assert x_result.size == 0
            assert y_result.size == 0
            return

        expected_x, expected_y = test_case.expected_result
        np.testing.assert_allclose(x_result, expected_x, rtol=1e-5)
        np.testing.assert_allclose(y_result, expected_y, rtol=1e-5)


class TestNormalize:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        id: str
        audio: Any
        expected_result: Union[np.ndarray, Type[Exception]]

    @pytest.mark.parametrize(
        "test_case",
        [
            TestCase(
                id="normalize_half_range", audio=np.array([0.5, -0.5, 0.25]), expected_result=np.array([1.0, -1.0, 0.5])
            ),
            TestCase(
                id="normalize_double_range",
                audio=np.array([2.0, -2.0, 1.0]),
                expected_result=np.array([1.0, -1.0, 0.5]),
            ),
            TestCase(
                id="normalize_small_values",
                audio=np.array([0.1, 0.2, 0.3]),
                expected_result=np.array([1.0 / 3, 2.0 / 3, 1.0]),
            ),
            TestCase(
                id="already_normalized", audio=np.array([1.0, 1.0, 1.0]), expected_result=np.array([1.0, 1.0, 1.0])
            ),
            TestCase(id="all_zeros", audio=np.array([0.0, 0.0, 0.0]), expected_result=np.array([0.0, 0.0, 0.0])),
            TestCase(id="empty_array", audio=np.array([]), expected_result=np.array([])),
            TestCase(
                id="nan_replaced_with_zero",
                audio=np.array([np.nan, 1.0, -1.0]),
                expected_result=np.array([0.0, 1.0, -1.0]),
            ),
            TestCase(
                id="inf_replaced_with_zero",
                audio=np.array([np.inf, 1.0, -1.0]),
                expected_result=np.array([0.0, 1.0, -1.0]),
            ),
            TestCase(
                id="neginf_replaced_with_zero",
                audio=np.array([-np.inf, 1.0, -1.0]),
                expected_result=np.array([0.0, 1.0, -1.0]),
            ),
            TestCase(
                id="all_invalid_becomes_zeros",
                audio=np.array([np.nan, np.inf, -np.inf]),
                expected_result=np.array([0.0, 0.0, 0.0]),
            ),
            TestCase(
                id="float32_dtype",
                audio=np.array([0.5], dtype=np.float32),
                expected_result=np.array([1.0], dtype=np.float32),
            ),
            TestCase(
                id="int32_normalized",
                audio=np.array([2, -4, 1], dtype=np.int32),
                expected_result=np.array([0.5, -1.0, 0.25]),
            ),
            TestCase(id="string_raises_type_error", audio="not an array", expected_result=TypeError),
            TestCase(id="list_raises_type_error", audio=[1.0, 2.0, 3.0], expected_result=TypeError),
            TestCase(id="none_raises_type_error", audio=None, expected_result=TypeError),
            TestCase(id="2d_raises_value_error", audio=np.array([[1, 2], [3, 4]]), expected_result=ValueError),
        ],
        ids=lambda tc: tc.id,
    )
    def test_normalize(self, test_case: TestCase) -> None:
        if expect_error(normalize, test_case.expected_result, test_case.audio):
            return

        result = normalize(test_case.audio)
        np.testing.assert_allclose(result, test_case.expected_result, rtol=1e-5)


class TestQuantize:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        id: str
        audio: Any
        levels: Any
        expected_result: Union[np.ndarray, Type[Exception]]

    @pytest.mark.parametrize(
        "test_case",
        [
            TestCase(
                id="three_levels",
                audio=np.array([0.0, 0.6, 1.0, -0.6, -1.0]),
                levels=3,
                expected_result=np.array([0.0, 1.0, 1.0, -1.0, -1.0]),
            ),
            TestCase(
                id="five_levels",
                audio=np.array([0.0, 0.3, 0.6, 0.8, 1.0]),
                levels=5,
                expected_result=np.array([0.0, 0.5, 0.5, 1.0, 1.0]),
            ),
            TestCase(
                id="seven_levels",
                audio=np.array([0.1, 0.2, 0.4]),
                levels=7,
                expected_result=np.array([0.0, 1.0 / 3, 1.0 / 3]),
            ),
            TestCase(id="single_value", audio=np.array([0.0]), levels=3, expected_result=np.array([0.0])),
            TestCase(id="empty_array", audio=np.array([]), levels=3, expected_result=np.array([])),
            TestCase(
                id="even_adjusted_to_odd", audio=np.array([0.6, -0.6]), levels=4, expected_result=np.array([1.0, -1.0])
            ),
            TestCase(
                id="float32_dtype",
                audio=np.array([0.6, -0.6], dtype=np.float32),
                levels=3,
                expected_result=np.array([1.0, -1.0], dtype=np.float32),
            ),
            TestCase(
                id="two_levels_raises_value_error", audio=np.array([0.5, -0.5]), levels=2, expected_result=ValueError
            ),
            TestCase(
                id="one_level_raises_value_error", audio=np.array([0.5, -0.5]), levels=1, expected_result=ValueError
            ),
            TestCase(
                id="zero_levels_raises_value_error", audio=np.array([0.5, -0.5]), levels=0, expected_result=ValueError
            ),
            TestCase(
                id="negative_levels_raises_value_error",
                audio=np.array([0.5, -0.5]),
                levels=-5,
                expected_result=ValueError,
            ),
            TestCase(
                id="float_levels_raises_type_error", audio=np.array([0.5, -0.5]), levels=3.5, expected_result=TypeError
            ),
            TestCase(
                id="string_levels_raises_type_error", audio=np.array([0.5, -0.5]), levels="3", expected_result=TypeError
            ),
            TestCase(
                id="none_levels_raises_type_error", audio=np.array([0.5, -0.5]), levels=None, expected_result=TypeError
            ),
            TestCase(id="string_audio_raises_type_error", audio="not an array", levels=3, expected_result=TypeError),
            TestCase(id="list_audio_raises_type_error", audio=[0.5, -0.5], levels=3, expected_result=TypeError),
            TestCase(id="none_audio_raises_type_error", audio=None, levels=3, expected_result=TypeError),
            TestCase(
                id="2d_audio_raises_value_error", audio=np.array([[1, 2], [3, 4]]), levels=3, expected_result=ValueError
            ),
        ],
        ids=lambda tc: tc.id,
    )
    def test_quantize(self, test_case: TestCase) -> None:
        if expect_error(quantize, test_case.expected_result, test_case.audio, test_case.levels):
            return

        result = quantize(test_case.audio, test_case.levels)
        np.testing.assert_allclose(result, test_case.expected_result, rtol=1e-5)
