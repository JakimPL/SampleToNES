from dataclasses import dataclass
from typing import Any, Type, Union

import numpy as np
import pytest

from sampletones.audio.validation import validate_audio_array, validate_buffer_size, validate_sample_rate
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
            TestCase(
                id="valid_float64_array",
                audio=np.array([1.0, 2.0, 3.0]),
                expected_result=None,
            ),
            TestCase(
                id="empty_array",
                audio=np.array([]),
                expected_result=None,
            ),
            TestCase(
                id="valid_float32_array",
                audio=np.array([1.0, 2.0, 3.0], dtype=np.float32),
                expected_result=None,
            ),
            TestCase(
                id="valid_int32_array",
                audio=np.array([1, 2, 3], dtype=np.int32),
                expected_result=None,
            ),
            TestCase(
                id="string_raises_type_error",
                audio="not an array",
                expected_result=TypeError,
            ),
            TestCase(
                id="list_raises_type_error",
                audio=[1.0, 2.0, 3.0],
                expected_result=TypeError,
            ),
            TestCase(
                id="none_raises_type_error",
                audio=None,
                expected_result=TypeError,
            ),
            TestCase(
                id="int_raises_type_error",
                audio=123,
                expected_result=TypeError,
            ),
            TestCase(
                id="2d_array_raises_value_error",
                audio=np.array([[1, 2], [3, 4]]),
                expected_result=ValueError,
            ),
            TestCase(
                id="3d_array_raises_value_error",
                audio=np.array([[[1]]]),
                expected_result=ValueError,
            ),
        ],
        ids=lambda tc: tc.id,
    )
    def test_validate_audio_array(self, test_case: TestCase) -> None:
        if expect_error(validate_audio_array, test_case.expected_result, test_case.audio):
            return

        validate_audio_array(test_case.audio)


class TestValidateSampleRate:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        id: str
        sample_rate: Any
        expected_result: Union[None, Type[Exception]]

    @pytest.mark.parametrize(
        "test_case",
        [
            TestCase(
                id="valid_8000",
                sample_rate=8000,
                expected_result=None,
            ),
            TestCase(
                id="valid_16000",
                sample_rate=16000,
                expected_result=None,
            ),
            TestCase(
                id="valid_22050",
                sample_rate=22050,
                expected_result=None,
            ),
            TestCase(
                id="valid_44100",
                sample_rate=44100,
                expected_result=None,
            ),
            TestCase(
                id="valid_48000",
                sample_rate=48000,
                expected_result=None,
            ),
            TestCase(
                id="valid_96000",
                sample_rate=96000,
                expected_result=None,
            ),
            TestCase(
                id="valid_192000",
                sample_rate=192000,
                expected_result=None,
            ),
            TestCase(
                id="invalid_rate_raises_value_error",
                sample_rate=12345,
                expected_result=ValueError,
            ),
            TestCase(
                id="zero_raises_value_error",
                sample_rate=0,
                expected_result=ValueError,
            ),
            TestCase(
                id="negative_raises_value_error",
                sample_rate=-44100,
                expected_result=ValueError,
            ),
            TestCase(
                id="float_raises_type_error",
                sample_rate=44100.0,
                expected_result=TypeError,
            ),
            TestCase(
                id="string_raises_type_error",
                sample_rate="44100",
                expected_result=TypeError,
            ),
            TestCase(
                id="none_raises_type_error",
                sample_rate=None,
                expected_result=TypeError,
            ),
            TestCase(
                id="list_raises_type_error",
                sample_rate=[44100],
                expected_result=TypeError,
            ),
        ],
        ids=lambda tc: tc.id,
    )
    def test_validate_sample_rate(self, test_case: TestCase) -> None:
        if expect_error(validate_sample_rate, test_case.expected_result, test_case.sample_rate):
            return

        validate_sample_rate(test_case.sample_rate)


class TestValidateBufferSize:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        id: str
        buffer_size: Any
        expected_result: Union[None, Type[Exception]]

    @pytest.mark.parametrize(
        "test_case",
        [
            TestCase(
                id="valid_256",
                buffer_size=256,
                expected_result=None,
            ),
            TestCase(
                id="valid_1024",
                buffer_size=1024,
                expected_result=None,
            ),
            TestCase(
                id="valid_2048",
                buffer_size=2048,
                expected_result=None,
            ),
            TestCase(
                id="valid_4096",
                buffer_size=4096,
                expected_result=None,
            ),
            TestCase(
                id="invalid_size_raises_value_error",
                buffer_size=1000,
                expected_result=ValueError,
            ),
            TestCase(
                id="zero_raises_value_error",
                buffer_size=0,
                expected_result=ValueError,
            ),
            TestCase(
                id="negative_raises_value_error",
                buffer_size=-1024,
                expected_result=ValueError,
            ),
            TestCase(
                id="float_raises_type_error",
                buffer_size=1024.0,
                expected_result=TypeError,
            ),
            TestCase(
                id="string_raises_type_error",
                buffer_size="1024",
                expected_result=TypeError,
            ),
            TestCase(
                id="none_raises_type_error",
                buffer_size=None,
                expected_result=TypeError,
            ),
            TestCase(
                id="list_raises_type_error",
                buffer_size=[1024],
                expected_result=TypeError,
            ),
        ],
        ids=lambda tc: tc.id,
    )
    def test_validate_buffer_size(self, test_case: TestCase) -> None:
        if expect_error(validate_buffer_size, test_case.expected_result, test_case.buffer_size):
            return

        validate_buffer_size(test_case.buffer_size)
