from dataclasses import dataclass
from typing import Optional, Tuple, Type, Union

import pytest

from sampletones_application.utils.color import parse_hex_color
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.errors import expect_error


class TestParseHexColor(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        value: str
        expected: Union[Tuple[int, int, int, int], Type[Exception]]

    test_cases = [
        # --- valid 6-digit (opaque, alpha defaults to 255) ---
        TestCase(
            label="black",
            value="#000000",
            expected=(0, 0, 0, 255),
        ),
        TestCase(
            label="white",
            value="#ffffff",
            expected=(255, 255, 255, 255),
        ),
        TestCase(
            label="uppercase_hex",
            value="#FFFFFF",
            expected=(255, 255, 255, 255),
        ),
        TestCase(
            label="mixed_case_hex",
            value="#AbCdEf",
            expected=(171, 205, 239, 255),
        ),
        TestCase(
            label="opaque_color",
            value="#64c8ff",
            expected=(100, 200, 255, 255),
        ),
        # --- valid 8-digit (explicit alpha) ---
        TestCase(
            label="fully_transparent",
            value="#00000000",
            expected=(0, 0, 0, 0),
        ),
        TestCase(
            label="fully_opaque_8digit",
            value="#ffffffff",
            expected=(255, 255, 255, 255),
        ),
        TestCase(
            label="partial_alpha",
            value="#c0202064",
            expected=(192, 32, 32, 100),
        ),
        TestCase(
            label="low_alpha",
            value="#ffffff18",
            expected=(255, 255, 255, 24),
        ),
        TestCase(
            label="small_alpha",
            value="#ffffff20",
            expected=(255, 255, 255, 32),
        ),
        # --- whitespace stripping ---
        TestCase(
            label="leading_whitespace",
            value="  #64c8ff",
            expected=(100, 200, 255, 255),
        ),
        TestCase(
            label="trailing_whitespace",
            value="#64c8ff  ",
            expected=(100, 200, 255, 255),
        ),
        TestCase(
            label="both_whitespace",
            value="  #64c8ff  ",
            expected=(100, 200, 255, 255),
        ),
        # --- missing or wrong prefix ---
        TestCase(
            label="no_hash_prefix",
            value="ffffff",
            expected=ValueError,
        ),
        TestCase(
            label="wrong_prefix_0x",
            value="0xffffff",
            expected=ValueError,
        ),
        TestCase(
            label="empty_string",
            value="",
            expected=ValueError,
        ),
        TestCase(
            label="hash_only",
            value="#",
            expected=ValueError,
        ),
        # --- wrong length ---
        TestCase(
            label="too_short_3digits",
            value="#fff",
            expected=ValueError,
        ),
        TestCase(
            label="seven_digits",
            value="#fffffff",
            expected=ValueError,
        ),
        TestCase(
            label="nine_digits",
            value="#fffffffff",
            expected=ValueError,
        ),
        TestCase(
            label="twelve_digits",
            value="#ffffffffffff",
            expected=ValueError,
        ),
        # --- non-hex characters ---
        TestCase(
            label="non_hex_letters",
            value="#gggggg",
            expected=ValueError,
        ),
        TestCase(
            label="non_hex_mixed",
            value="#xyz123",
            expected=ValueError,
        ),
        TestCase(
            label="contains_space_inside",
            value="#ff ff ff",
            expected=ValueError,
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_parse_hex_color(self, test_case: TestCase) -> None:
        if expect_error(parse_hex_color, test_case.expected, test_case.value):
            return

        assert parse_hex_color(test_case.value) == test_case.expected
