from dataclasses import dataclass
from typing import Any, Type, Union

import pytest

from sampletones_core.constants.general import MAX_PERIOD, MAX_PITCH, MIN_PITCH
from sampletones_core.utils.frequencies import (
    clamp_period,
    clamp_pitch,
    is_pitch_valid,
    period_to_name,
    pitch_to_name,
    sanitize,
    sanitize_period,
    sanitize_pitch,
    validate_period,
)
from sampletones_shared.constants.music import LIMIT_MAX_PITCH, LIMIT_MIN_PITCH
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.errors import expect_error


class TestIsPitchValid:
    def test_is_pitch_valid(self) -> None:
        valid_pitches = range(MIN_PITCH, MAX_PITCH + 1)
        for pitch in valid_pitches:
            assert is_pitch_valid(pitch), pitch

        invalid_pitches = (
            0,
            LIMIT_MIN_PITCH,
            MIN_PITCH - 1,
            MAX_PITCH + 1,
            LIMIT_MAX_PITCH,
            128,
        )
        for pitch in invalid_pitches:
            assert not is_pitch_valid(pitch), pitch


class TestValidatePeriod(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[None, Type[Exception]]
        period: Any

    test_cases = (
        TestCase(
            period=0,
            expected=None,
            label="zero_minimum",
        ),
        TestCase(
            period=MAX_PERIOD,
            expected=None,
            label="exactly_max_period",
        ),
        TestCase(
            period=5,
            expected=None,
            label="middle_valid_period",
        ),
        TestCase(
            period=1,
            expected=None,
            label="one",
        ),
        TestCase(
            period=MAX_PERIOD - 1,
            expected=None,
            label="one_below_max",
        ),
        TestCase(
            period=MAX_PERIOD // 2,
            expected=None,
            label="middle_of_range",
        ),
        TestCase(
            period=-1,
            expected=ValueError,
            label="negative_one",
        ),
        TestCase(
            period=MAX_PERIOD + 1,
            expected=ValueError,
            label="one_above_max",
        ),
        TestCase(
            period=-100,
            expected=ValueError,
            label="large_negative",
        ),
        TestCase(
            period=100,
            expected=ValueError,
            label="large_positive",
        ),
        TestCase(
            period="5",
            expected=TypeError,
            label="period_string",
        ),
        TestCase(
            period=None,
            expected=TypeError,
            label="period_none",
        ),
        TestCase(
            period=5.5,
            expected=TypeError,
            label="period_float",
        ),
        TestCase(
            period=[5],
            expected=TypeError,
            label="period_list",
        ),
        TestCase(
            period={"period": 5},
            expected=TypeError,
            label="period_dict",
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_validate_period(self, test_case: TestCase) -> None:
        if expect_error(validate_period, test_case.expected, test_case.period):
            return

        validate_period(test_case.period)


class TestPitchToName(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[str, Type[Exception]]
        pitch: Any
        transpose: Any

    test_cases = (
        TestCase(
            pitch=60,
            transpose=0,
            expected="C-3",
            label="middle_c",
        ),
        TestCase(
            pitch=69,
            transpose=0,
            expected="A-3",
            label="a3",
        ),
        TestCase(
            pitch=61,
            transpose=0,
            expected="C#3",
            label="c_sharp_3",
        ),
        TestCase(
            pitch=60,
            transpose=2,
            expected="D-3",
            label="middle_c_transpose_up_2",
        ),
        TestCase(
            pitch=60,
            transpose=-12,
            expected="C-2",
            label="middle_c_transpose_down_octave",
        ),
        TestCase(
            pitch=MIN_PITCH,
            transpose=0,
            expected="A-0",
            label="min_pitch",
        ),
        TestCase(
            pitch=MAX_PITCH,
            transpose=0,
            expected="B-7",
            label="max_pitch",
        ),
        TestCase(
            pitch=0,
            transpose=0,
            expected=ValueError,
            label="pitch_zero",
        ),
        TestCase(
            pitch=24,
            transpose=0,
            expected="C-0",
            label="minimum_valid_pitch",
        ),
        TestCase(
            pitch=-1,
            transpose=0,
            expected=ValueError,
            label="negative_pitch",
        ),
        TestCase(
            pitch=24,
            transpose=-1,
            expected=ValueError,
            label="invalid_pitch_after_transpose",
        ),
        TestCase(
            pitch=127,
            transpose=0,
            expected="G-8",
            label="max_midi_pitch",
        ),
        TestCase(
            pitch=60.0,
            transpose=12,
            expected=TypeError,
            label="pitch_float",
        ),
        TestCase(
            pitch=60,
            transpose=0.0,
            expected=TypeError,
            label="transpose_float",
        ),
        TestCase(
            pitch=60,
            transpose=None,
            expected=TypeError,
            label="transpose_none",
        ),
        TestCase(
            pitch=None,
            transpose=0,
            expected=TypeError,
            label="pitch_none",
        ),
        TestCase(
            pitch="60",
            transpose=0,
            expected=TypeError,
            label="pitch_string",
        ),
        TestCase(
            pitch=None,
            transpose=0,
            expected=TypeError,
            label="pitch_none",
        ),
        TestCase(
            pitch=[60],
            transpose=0,
            expected=TypeError,
            label="pitch_list",
        ),
        TestCase(
            pitch={"pitch": 60},
            transpose=0,
            expected=TypeError,
            label="pitch_dict",
        ),
        TestCase(
            pitch=60.5,
            transpose=0,
            expected=TypeError,
            label="pitch_float",
        ),
        TestCase(
            pitch=60,
            transpose="2",
            expected=TypeError,
            label="transpose_string",
        ),
        TestCase(
            pitch=60,
            transpose=None,
            expected=TypeError,
            label="transpose_none",
        ),
        TestCase(
            pitch=60,
            transpose=[2],
            expected=TypeError,
            label="transpose_list",
        ),
        TestCase(
            pitch=60,
            transpose=2.5,
            expected=TypeError,
            label="transpose_float",
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_pitch_to_name(self, test_case: TestCase) -> None:
        if expect_error(
            pitch_to_name,
            test_case.expected,
            test_case.pitch,
            test_case.transpose,
        ):
            return

        result = pitch_to_name(test_case.pitch, test_case.transpose)
        assert result == test_case.expected


class TestPeriodToName(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[str, Type[Exception]]
        period: Any

    test_cases = (
        TestCase(
            period=0,
            expected="0-#",
            label="period_0",
        ),
        TestCase(
            period=10,
            expected="A-#",
            label="period_10",
        ),
        TestCase(
            period=15,
            expected="F-#",
            label="period_15_max",
        ),
        TestCase(
            period=1,
            expected="1-#",
            label="period_1",
        ),
        TestCase(
            period=9,
            expected="9-#",
            label="period_9",
        ),
        TestCase(
            period=11,
            expected="B-#",
            label="period_11",
        ),
        TestCase(
            period=-1,
            expected=ValueError,
            label="period_negative",
        ),
        TestCase(
            period=100,
            expected=ValueError,
            label="period_too_large",
        ),
        TestCase(
            period="10",
            expected=TypeError,
            label="period_string",
        ),
        TestCase(
            period=None,
            expected=TypeError,
            label="period_none",
        ),
        TestCase(
            period=[10],
            expected=TypeError,
            label="period_list",
        ),
        TestCase(
            period={"period": 10},
            expected=TypeError,
            label="period_dict",
        ),
        TestCase(
            period=10.0,
            expected=TypeError,
            label="period_float",
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_period_to_name(self, test_case: TestCase) -> None:
        if expect_error(period_to_name, test_case.expected, test_case.period):
            return

        result = period_to_name(test_case.period)
        assert result == test_case.expected


class TestClampPitch(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[int, Type[Exception]]
        pitch: Any
        min_pitch: Any
        max_pitch: Any

    test_cases = (
        TestCase(
            pitch=60,
            min_pitch=MIN_PITCH,
            max_pitch=MAX_PITCH,
            expected=60,
            label="within_range",
        ),
        TestCase(
            pitch=0,
            min_pitch=MIN_PITCH,
            max_pitch=MAX_PITCH,
            expected=MIN_PITCH,
            label="below_minimum",
        ),
        TestCase(
            pitch=150,
            min_pitch=MIN_PITCH,
            max_pitch=MAX_PITCH,
            expected=MAX_PITCH,
            label="above_maximum",
        ),
        TestCase(
            pitch=MIN_PITCH,
            min_pitch=MIN_PITCH,
            max_pitch=MAX_PITCH,
            expected=MIN_PITCH,
            label="exactly_minimum",
        ),
        TestCase(
            pitch=MAX_PITCH,
            min_pitch=MIN_PITCH,
            max_pitch=MAX_PITCH,
            expected=MAX_PITCH,
            label="exactly_maximum",
        ),
        TestCase(
            pitch=-100,
            min_pitch=MIN_PITCH,
            max_pitch=MAX_PITCH,
            expected=MIN_PITCH,
            label="large_negative",
        ),
        TestCase(
            pitch=1000,
            min_pitch=MIN_PITCH,
            max_pitch=MAX_PITCH,
            expected=MAX_PITCH,
            label="large_positive",
        ),
        TestCase(
            pitch=60,
            min_pitch=50,
            max_pitch=70,
            expected=60,
            label="custom_range_within",
        ),
        TestCase(
            pitch=40,
            min_pitch=50,
            max_pitch=70,
            expected=50,
            label="custom_range_below",
        ),
        TestCase(
            pitch=80,
            min_pitch=50,
            max_pitch=70,
            expected=70,
            label="custom_range_above",
        ),
        TestCase(
            pitch=60,
            min_pitch=LIMIT_MIN_PITCH,
            max_pitch=LIMIT_MAX_PITCH,
            expected=60,
            label="possible_range",
        ),
        TestCase(
            pitch=60,
            min_pitch=60,
            max_pitch=60,
            expected=60,
            label="single_value_range",
        ),
        TestCase(
            pitch=10,
            min_pitch=60,
            max_pitch=60,
            expected=60,
            label="single_value_range_outside",
        ),
        TestCase(
            pitch=32,
            min_pitch=40,
            max_pitch=30,
            expected=ValueError,
            label="min_greater_than_max",
        ),
        TestCase(
            pitch="60",
            min_pitch=MIN_PITCH,
            max_pitch=MAX_PITCH,
            expected=TypeError,
            label="pitch_string",
        ),
        TestCase(
            pitch=None,
            min_pitch=MIN_PITCH,
            max_pitch=MAX_PITCH,
            expected=TypeError,
            label="pitch_none",
        ),
        TestCase(
            pitch=[60],
            min_pitch=MIN_PITCH,
            max_pitch=MAX_PITCH,
            expected=TypeError,
            label="pitch_list",
        ),
        TestCase(
            pitch=60,
            min_pitch="33",
            max_pitch=MAX_PITCH,
            expected=TypeError,
            label="min_pitch_string",
        ),
        TestCase(
            pitch=60,
            min_pitch=MIN_PITCH,
            max_pitch="119",
            expected=TypeError,
            label="max_pitch_string",
        ),
        TestCase(
            pitch=60,
            min_pitch=None,
            max_pitch=MAX_PITCH,
            expected=TypeError,
            label="min_pitch_none",
        ),
        TestCase(
            pitch=60,
            min_pitch=MIN_PITCH,
            max_pitch=None,
            expected=TypeError,
            label="max_pitch_none",
        ),
        TestCase(
            pitch=60.0,
            min_pitch=MIN_PITCH,
            max_pitch=MAX_PITCH,
            expected=TypeError,
            label="pitch_float",
        ),
        TestCase(
            pitch=60,
            min_pitch=MIN_PITCH,
            max_pitch=LIMIT_MAX_PITCH + 1,
            expected=ValueError,
            label="max_pitch_out_of_bounds",
        ),
        TestCase(
            pitch=60,
            min_pitch=LIMIT_MIN_PITCH - 1,
            max_pitch=LIMIT_MAX_PITCH,
            expected=ValueError,
            label="min_pitch_out_of_bounds",
        ),
        TestCase(
            pitch=60,
            min_pitch=LIMIT_MIN_PITCH,
            max_pitch=LIMIT_MAX_PITCH + 1,
            expected=ValueError,
            label="max_pitch_out_of_bounds",
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_clamp_pitch(self, test_case: TestCase) -> None:
        if expect_error(
            clamp_pitch,
            test_case.expected,
            test_case.pitch,
            test_case.min_pitch,
            test_case.max_pitch,
        ):
            return

        result = clamp_pitch(test_case.pitch, test_case.min_pitch, test_case.max_pitch)
        assert result == test_case.expected
        assert isinstance(result, int)


class TestClampPeriod(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[int, Type[Exception]]
        period: Any

    test_cases = (
        TestCase(
            period=5,
            expected=5,
            label="within_range",
        ),
        TestCase(
            period=-10,
            expected=0,
            label="below_minimum",
        ),
        TestCase(
            period=100,
            expected=MAX_PERIOD,
            label="above_maximum",
        ),
        TestCase(
            period=0,
            expected=0,
            label="exactly_minimum",
        ),
        TestCase(
            period=MAX_PERIOD,
            expected=MAX_PERIOD,
            label="exactly_maximum",
        ),
        TestCase(
            period=-1000,
            expected=0,
            label="large_negative",
        ),
        TestCase(
            period=1000,
            expected=MAX_PERIOD,
            label="large_positive",
        ),
        TestCase(
            period="5",
            expected=TypeError,
            label="period_string",
        ),
        TestCase(
            period=None,
            expected=TypeError,
            label="period_none",
        ),
        TestCase(
            period=[5],
            expected=TypeError,
            label="period_list",
        ),
        TestCase(
            period=5.0,
            expected=5,
            label="period_float",
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_clamp_period(self, test_case: TestCase) -> None:
        if expect_error(
            clamp_period,
            test_case.expected,
            test_case.period,
        ):
            return

        result = clamp_period(test_case.period)
        assert result == test_case.expected
        assert isinstance(result, int)


class TestSanitize(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[str, Type[Exception]]
        name: Any

    test_cases = (
        TestCase(
            name="  hello world  ",
            expected="HELLO WORLD",
            label="strip_and_uppercase",
        ),
        TestCase(
            name="c#4",
            expected="C#4",
            label="lowercase_to_uppercase",
        ),
        TestCase(
            name="  A4  ",
            expected="A4",
            label="strip_whitespace",
        ),
        TestCase(
            name="ALREADY UPPER",
            expected="ALREADY UPPER",
            label="already_uppercase",
        ),
        TestCase(
            name="",
            expected="",
            label="empty_string",
        ),
        TestCase(
            name="   ",
            expected="",
            label="only_whitespace",
        ),
        TestCase(
            name="MiXeD CaSe",
            expected="MIXED CASE",
            label="mixed_case",
        ),
        TestCase(
            name="\t\n  test  \n\t",
            expected="TEST",
            label="various_whitespace",
        ),
        TestCase(
            name="a",
            expected="A",
            label="single_character",
        ),
        TestCase(
            name="123",
            expected="123",
            label="digits_only",
        ),
        TestCase(
            name="special!@#$%^&*()",
            expected="SPECIAL!@#$%^&*()",
            label="special_characters",
        ),
        TestCase(
            name=None,
            expected=AttributeError,
            label="name_none",
        ),
        TestCase(
            name=123,
            expected=AttributeError,
            label="name_int",
        ),
        TestCase(
            name=["test"],
            expected=AttributeError,
            label="name_list",
        ),
        TestCase(
            name={"name": "test"},
            expected=AttributeError,
            label="name_dict",
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_sanitize(self, test_case: TestCase) -> None:
        if expect_error(sanitize, test_case.expected, test_case.name):
            return

        result = sanitize(test_case.name)
        assert result == test_case.expected


class TestSanitizePitch(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[str, Type[Exception]]
        name: Any

    test_cases = (
        TestCase(
            name="C#4",
            expected="C#4",
            label="valid_pitch_name",
        ),
        TestCase(
            name="  a#3  ",
            expected="A#3",
            label="lowercase_with_whitespace",
        ),
        TestCase(
            name="C@4!",
            expected="C4",
            label="invalid_characters_removed",
        ),
        TestCase(
            name="F-#",
            expected="F-#",
            label="period_format",
        ),
        TestCase(
            name="",
            expected="",
            label="empty_string",
        ),
        TestCase(
            name="xyz",
            expected="",
            label="no_valid_characters",
        ),
        TestCase(
            name="A0",
            expected="A0",
            label="note_with_octave",
        ),
        TestCase(
            name="D#5",
            expected="D#5",
            label="sharp_note",
        ),
        TestCase(
            name="123456789",
            expected="123456789",
            label="all_digits",
        ),
        TestCase(
            name="ABCDEF",
            expected="ABCDEF",
            label="all_hex_letters",
        ),
        TestCase(
            name="0-#",
            expected="0-#",
            label="period_format_0",
        ),
        TestCase(
            name="a#3 test",
            expected="A#3E",
            label="extra_text_a-f_stayed",
        ),
        TestCase(
            name="G--",
            expected="--",
            label="multiple_hyphens_g_removed",
        ),
        TestCase(
            name="C##4",
            expected="C##4",
            label="double_sharp",
        ),
        TestCase(
            name=None,
            expected=AttributeError,
            label="name_none",
        ),
        TestCase(
            name=123,
            expected=AttributeError,
            label="name_int",
        ),
        TestCase(
            name=["C#4"],
            expected=AttributeError,
            label="name_list",
        ),
        TestCase(
            name={"name": "C#4"},
            expected=AttributeError,
            label="name_dict",
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_sanitize_pitch(self, test_case: TestCase) -> None:
        if expect_error(sanitize_pitch, test_case.expected, test_case.name):
            return

        result = sanitize_pitch(test_case.name)
        assert result == test_case.expected


class TestSanitizePeriod(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[str, Type[Exception]]
        name: Any

    test_cases = (
        TestCase(
            name="0A",
            expected="0A",
            label="hex_digits",
        ),
        TestCase(
            name="  f  ",
            expected="F",
            label="lowercase_with_whitespace",
        ),
        TestCase(
            name="A-#",
            expected="A",
            label="period_format_stripped",
        ),
        TestCase(
            name="10@!",
            expected="10",
            label="invalid_characters_removed",
        ),
        TestCase(
            name="",
            expected="",
            label="empty_string",
        ),
        TestCase(
            name="xyz",
            expected="",
            label="no_valid_characters",
        ),
        TestCase(
            name="123456789",
            expected="123456789",
            label="all_digits",
        ),
        TestCase(
            name="ABCDEF",
            expected="ABCDEF",
            label="all_hex_letters",
        ),
        TestCase(
            name="0123456789ABCDEF",
            expected="0123456789ABCDEF",
            label="all_hex_characters",
        ),
        TestCase(
            name="ghijklmnop",
            expected="",
            label="non_hex_letters",
        ),
        TestCase(
            name="F-#",
            expected="F",
            label="f_period_format",
        ),
        TestCase(
            name="1a2b3c",
            expected="1A2B3C",
            label="mixed_hex",
        ),
        TestCase(
            name="!@#$%^&*()",
            expected="",
            label="only_special_characters",
        ),
        TestCase(
            name="   ",
            expected="",
            label="only_whitespace",
        ),
        TestCase(
            name=None,
            expected=AttributeError,
            label="name_none",
        ),
        TestCase(
            name=123,
            expected=AttributeError,
            label="name_int",
        ),
        TestCase(
            name=["0A"],
            expected=AttributeError,
            label="name_list",
        ),
        TestCase(
            name={"name": "0A"},
            expected=AttributeError,
            label="name_dict",
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_sanitize_period(self, test_case: TestCase) -> None:
        if expect_error(sanitize_period, test_case.expected, test_case.name):
            return

        result = sanitize_period(test_case.name)
        assert result == test_case.expected
