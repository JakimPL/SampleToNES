from dataclasses import dataclass
from typing import Tuple, Type, Union

import pytest

from sampletones_shared.utils.color import blend, composite, parse_hex_color, to_grayscale
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.errors import expect_error


class TestParseHexColor(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        value: str
        expected: Union[Tuple[int, int, int, int], Type[Exception]]

    test_cases = (
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
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_parse_hex_color(self, test_case: TestCase) -> None:
        if expect_error(parse_hex_color, test_case.expected, test_case.value):
            return

        assert parse_hex_color(test_case.value) == test_case.expected


class TestToGrayscale:
    def test_collapses_rgb_to_luminance(self) -> None:
        assert to_grayscale((255, 200, 100, 255)) == (205, 205, 205, 255)

    def test_preserves_alpha(self) -> None:
        assert to_grayscale((255, 200, 100, 40)) == (205, 205, 205, 40)

    def test_gray_stays_gray(self) -> None:
        assert to_grayscale((128, 128, 128, 255)) == (128, 128, 128, 255)


class TestComposite:
    TRANSPARENT = (0, 0, 0, 0)
    FAINT_WHITE = (255, 255, 255, 16)
    GREEN = (100, 220, 100, 64)

    def test_an_opaque_overlay_covers_what_is_under_it(self) -> None:
        assert composite(self.GREEN, (10, 20, 30, 255)) == (10, 20, 30, 255)

    def test_a_transparent_overlay_leaves_the_base(self) -> None:
        assert composite(self.GREEN, self.TRANSPARENT) == self.GREEN

    def test_a_transparent_base_leaves_the_overlay(self) -> None:
        assert composite(self.TRANSPARENT, self.GREEN) == self.GREEN

    def test_two_transparent_colours_stay_transparent(self) -> None:
        assert composite(self.TRANSPARENT, self.TRANSPARENT) == self.TRANSPARENT

    def test_stacked_washes_cover_more_than_either_alone(self) -> None:
        red, green, blue, alpha = composite(self.FAINT_WHITE, self.GREEN)

        assert alpha == 76
        assert (red, green, blue) == (124, 226, 124)


class TestBlend:
    START = (0, 0, 0, 0)
    END = (100, 200, 40, 255)

    def test_zero_fraction_returns_start(self) -> None:
        assert blend(self.START, self.END, 0.0) == self.START

    def test_one_fraction_returns_end(self) -> None:
        assert blend(self.START, self.END, 1.0) == self.END

    def test_halfway_mixes_each_channel(self) -> None:
        assert blend(self.START, self.END, 0.5) == (50, 100, 20, 128)

    def test_clamps_below_zero(self) -> None:
        assert blend(self.START, self.END, -1.0) == self.START

    def test_clamps_above_one(self) -> None:
        assert blend(self.START, self.END, 2.0) == self.END
