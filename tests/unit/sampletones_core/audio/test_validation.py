from dataclasses import dataclass
from typing import Any, Tuple, Type, Union

import numpy as np
import pytest

from sampletones_core.audio.validation import (
    validate_audio_array,
    validate_buffer_size,
    validate_sample_rate,
)
from sampletones_core.constants.audio import MAX_SAMPLE_RATE, MIN_SAMPLE_RATE, SAMPLE_RATES
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.errors import expect_error


class TestValidateAudioArray(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[None, Type[Exception]]
        audio: Any
        allowed_dims: Tuple[int, ...] = (1,)

    test_cases = (
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
    )

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

        validate_audio_array(
            test_case.audio,
            allowed_dims=test_case.allowed_dims,
        )


class TestValidateSampleRate(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[None, Type[Exception]]
        sample_rate: Any

    test_cases = (
        TestCase(
            label="lowest_accepted_rate",
            sample_rate=MIN_SAMPLE_RATE,
            expected=None,
        ),
        TestCase(
            label="highest_accepted_rate",
            sample_rate=MAX_SAMPLE_RATE,
            expected=None,
        ),
        TestCase(
            label="rate_missing_from_the_offered_list_is_accepted",
            sample_rate=11025,
            expected=None,
        ),
        TestCase(
            label="arbitrary_rate_within_range_is_accepted",
            sample_rate=12345,
            expected=None,
        ),
        TestCase(
            label="just_below_range_raises_value_error",
            sample_rate=MIN_SAMPLE_RATE - 1,
            expected=ValueError,
        ),
        TestCase(
            label="just_above_range_raises_value_error",
            sample_rate=MAX_SAMPLE_RATE + 1,
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
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_validate_sample_rate(self, test_case: TestCase) -> None:
        if expect_error(
            validate_sample_rate,
            test_case.expected,
            test_case.sample_rate,
        ):
            return

        validate_sample_rate(test_case.sample_rate)

    @pytest.mark.parametrize("sample_rate", SAMPLE_RATES)
    def test_every_offered_rate_is_accepted(self, sample_rate: int) -> None:
        validate_sample_rate(sample_rate)


class TestValidateBufferSize(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[None, Type[Exception]]
        buffer_size: Any

    test_cases = (
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
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_validate_buffer_size(self, test_case: TestCase) -> None:
        if expect_error(
            validate_buffer_size,
            test_case.expected,
            test_case.buffer_size,
        ):
            return

        validate_buffer_size(test_case.buffer_size)
