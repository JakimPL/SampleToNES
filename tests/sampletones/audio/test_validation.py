from dataclasses import dataclass
from typing import Any, Tuple, Type, Union

import numpy as np
import pytest

from sampletones.audio.validation import validate_audio_array, validate_buffer_size, validate_sample_rate
from tests.sampletones.errors import expect_error
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.parametrize import parametrized


class TestValidateAudioArray(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[None, Type[Exception]]
        audio: Any
        allowed_dims: Tuple[int, ...] = (1,)

    test_cases = [
        TestCase(
            label="valid_float64_array",
            audio=np.array([1.0, 2.0, 3.0]),
            expected=None,
        ),
        TestCase(
            label="empty_array",
            audio=np.array([]),
            expected=None,
        ),
        TestCase(
            label="valid_float32_array",
            audio=np.array([1.0, 2.0, 3.0], dtype=np.float32),
            expected=None,
        ),
        TestCase(
            label="valid_int32_array",
            audio=np.array([1, 2, 3], dtype=np.int32),
            expected=None,
        ),
        TestCase(
            label="invalid_object_array",
            audio=np.array(["1", "2", "3"], dtype=object),
            expected=TypeError,
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
            label="int_raises_type_error",
            audio=123,
            expected=TypeError,
        ),
        TestCase(
            label="2d_array_raises_value_error",
            audio=np.array([[1, 2], [3, 4]]),
            expected=ValueError,
        ),
        TestCase(
            label="3d_array_raises_value_error",
            audio=np.array([[[1]]]),
            expected=ValueError,
        ),
        TestCase(
            label="allowed_2d_array",
            audio=np.array([[1.0, 2.0], [3.0, 4.0]]),
            expected=None,
            allowed_dims=(1, 2),
        ),
        TestCase(
            label="not_allowed_3d_array",
            audio=np.array([[[1.0, 2.0], [3.0, 4.0]]]),
            expected=ValueError,
            allowed_dims=(1, 2),
        ),
        TestCase(
            label="empty_dimentsions",
            audio=np.array([1]),
            expected=ValueError,
            allowed_dims=(),
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_validate_audio_array(self, test_case: TestCase) -> None:
        if expect_error(
            validate_audio_array,
            test_case.expected,
            test_case.audio,
            allowed_dims=test_case.allowed_dims,
        ):
            return

        validate_audio_array(test_case.audio, allowed_dims=test_case.allowed_dims)


class TestValidateSampleRate(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[None, Type[Exception]]
        sample_rate: Any

    test_cases = [
        TestCase(
            label="valid_8000",
            sample_rate=8000,
            expected=None,
        ),
        TestCase(
            label="valid_16000",
            sample_rate=16000,
            expected=None,
        ),
        TestCase(
            label="valid_22050",
            sample_rate=22050,
            expected=None,
        ),
        TestCase(
            label="valid_44100",
            sample_rate=44100,
            expected=None,
        ),
        TestCase(
            label="valid_48000",
            sample_rate=48000,
            expected=None,
        ),
        TestCase(
            label="valid_96000",
            sample_rate=96000,
            expected=None,
        ),
        TestCase(
            label="valid_192000",
            sample_rate=192000,
            expected=None,
        ),
        TestCase(
            label="invalid_rate_raises_value_error",
            sample_rate=12345,
            expected=ValueError,
        ),
        TestCase(
            label="zero_raises_value_error",
            sample_rate=0,
            expected=ValueError,
        ),
        TestCase(
            label="negative_raises_value_error",
            sample_rate=-44100,
            expected=ValueError,
        ),
        TestCase(
            label="float_raises_type_error",
            sample_rate=44100.0,
            expected=TypeError,
        ),
        TestCase(
            label="string_raises_type_error",
            sample_rate="44100",
            expected=TypeError,
        ),
        TestCase(
            label="none_raises_type_error",
            sample_rate=None,
            expected=TypeError,
        ),
        TestCase(
            label="list_raises_type_error",
            sample_rate=[44100],
            expected=TypeError,
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_validate_sample_rate(self, test_case: TestCase) -> None:
        if expect_error(validate_sample_rate, test_case.expected, test_case.sample_rate):
            return

        validate_sample_rate(test_case.sample_rate)


class TestValidateBufferSize(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[None, Type[Exception]]
        buffer_size: Any

    test_cases = [
        TestCase(
            label="valid_256",
            buffer_size=256,
            expected=None,
        ),
        TestCase(
            label="valid_1024",
            buffer_size=1024,
            expected=None,
        ),
        TestCase(
            label="valid_2048",
            buffer_size=2048,
            expected=None,
        ),
        TestCase(
            label="valid_4096",
            buffer_size=4096,
            expected=None,
        ),
        TestCase(
            label="invalid_size_raises_value_error",
            buffer_size=1000,
            expected=ValueError,
        ),
        TestCase(
            label="zero_raises_value_error",
            buffer_size=0,
            expected=ValueError,
        ),
        TestCase(
            label="negative_raises_value_error",
            buffer_size=-1024,
            expected=ValueError,
        ),
        TestCase(
            label="float_raises_type_error",
            buffer_size=1024.0,
            expected=TypeError,
        ),
        TestCase(
            label="string_raises_type_error",
            buffer_size="1024",
            expected=TypeError,
        ),
        TestCase(
            label="none_raises_type_error",
            buffer_size=None,
            expected=TypeError,
        ),
        TestCase(
            label="list_raises_type_error",
            buffer_size=[1024],
            expected=TypeError,
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_validate_buffer_size(self, test_case: TestCase) -> None:
        if expect_error(validate_buffer_size, test_case.expected, test_case.buffer_size):
            return

        validate_buffer_size(test_case.buffer_size)
