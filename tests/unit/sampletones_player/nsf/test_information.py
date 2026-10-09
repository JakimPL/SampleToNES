from dataclasses import dataclass
from typing import Final

import pytest

from sampletones_player.nsf.information import (
    TEXT_ENCODING,
    NSFInformation,
    field_size,
    fit_field,
)
from sampletones_player.specification.nsf import (
    STRING_FIELD_SIZE,
    STRING_TEXT_SIZE,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

WIDE_CHARACTER: Final[str] = "ü"
SHORT_TEXT: Final[str] = "Rainy Day Theme"


class TestFitField(BaseTestSuite):
    """The part of a text a header string field holds in front of its terminator."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        text: str
        expected: str

    test_cases = (
        TestCase(label="short text", text=SHORT_TEXT, expected=SHORT_TEXT),
        TestCase(label="empty text", text="", expected=""),
        TestCase(
            label="exactly the room",
            text="A" * STRING_TEXT_SIZE,
            expected="A" * STRING_TEXT_SIZE,
        ),
        TestCase(
            label="one byte over",
            text="A" * STRING_FIELD_SIZE,
            expected="A" * STRING_TEXT_SIZE,
        ),
        TestCase(
            label="a character straddling the edge",
            text="A" * (STRING_TEXT_SIZE - 1) + WIDE_CHARACTER,
            expected="A" * (STRING_TEXT_SIZE - 1),
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_field_holds_the_text_that_fits(self, test_case: TestCase) -> None:
        assert fit_field(test_case.text) == test_case.expected

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_text_leaves_room_for_the_terminator(self, test_case: TestCase) -> None:
        assert len(fit_field(test_case.text).encode(TEXT_ENCODING)) < STRING_FIELD_SIZE


class TestFieldSize:
    def test_a_wide_character_takes_the_bytes_it_is_encoded_in(self) -> None:
        assert field_size(SHORT_TEXT + WIDE_CHARACTER) == len(SHORT_TEXT) + len(WIDE_CHARACTER.encode(TEXT_ENCODING))

    def test_a_fitted_text_takes_the_field_at_most(self) -> None:
        assert field_size(fit_field(WIDE_CHARACTER * STRING_FIELD_SIZE)) <= STRING_TEXT_SIZE


class TestNSFInformation:
    """Each text field is held as the part of itself the header carries."""

    def test_every_field_is_held_as_it_fits(self) -> None:
        overlong = "B" * STRING_FIELD_SIZE
        information = NSFInformation(title=overlong, artist=overlong, copyright=overlong)
        assert {
            information.title,
            information.artist,
            information.copyright,
        } == {fit_field(overlong)}
