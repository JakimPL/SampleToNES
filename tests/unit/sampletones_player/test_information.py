from dataclasses import dataclass
from typing import Final

import pytest
from pydantic import ValidationError

from sampletones_player.information import ProgramInformation, TextLine
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

WIDE_CHARACTER: Final[str] = "ü"
SHORT_TEXT: Final[str] = "Rainy Day Theme"
BYTE_ENCODING: Final[str] = "utf-8"
GLYPH_ENCODING: Final[str] = "ascii"
ROOM: Final[int] = 31
BYTE_LINE: Final[TextLine] = TextLine(encoding=BYTE_ENCODING, room=ROOM)
GLYPH_LINE: Final[TextLine] = TextLine(encoding=GLYPH_ENCODING, room=ROOM)


class TestFit(BaseTestSuite):
    """The part of a text a line holds in the room it has."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        text: str
        expected: str

    test_cases = (
        TestCase(label="short text", text=SHORT_TEXT, expected=SHORT_TEXT),
        TestCase(label="empty text", text="", expected=""),
        TestCase(
            label="exactly the room",
            text="A" * ROOM,
            expected="A" * ROOM,
        ),
        TestCase(
            label="one unit over",
            text="A" * (ROOM + 1),
            expected="A" * ROOM,
        ),
        TestCase(
            label="a character straddling the edge",
            text="A" * (ROOM - 1) + WIDE_CHARACTER,
            expected="A" * (ROOM - 1),
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_line_holds_the_text_that_fits(self, test_case: TestCase) -> None:
        assert BYTE_LINE.fit(test_case.text) == test_case.expected

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_fitted_text_takes_the_room_at_most(self, test_case: TestCase) -> None:
        assert BYTE_LINE.size(BYTE_LINE.fit(test_case.text)) <= ROOM

    def test_a_character_the_encoding_has_no_code_for_is_held_as_its_replacement_mark(self) -> None:
        assert GLYPH_LINE.fit(SHORT_TEXT + WIDE_CHARACTER) == SHORT_TEXT + "?"


class TestSize:
    """The units a text takes on a line, counted in the line's own encoding."""

    def test_a_wide_character_takes_the_bytes_it_is_encoded_in(self) -> None:
        assert BYTE_LINE.size(SHORT_TEXT + WIDE_CHARACTER) == len(SHORT_TEXT) + len(
            WIDE_CHARACTER.encode(BYTE_ENCODING)
        )

    def test_a_replaced_character_takes_one_unit(self) -> None:
        assert GLYPH_LINE.size(SHORT_TEXT + WIDE_CHARACTER) == len(SHORT_TEXT) + 1


class TestTextLine:
    def test_a_line_holding_nothing_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            TextLine(encoding=BYTE_ENCODING, room=0)


class TestProgramInformation:
    """The text is kept as given, and each kind of file carries the part of it that fits."""

    def test_the_text_is_kept_as_it_was_given(self) -> None:
        overlong = "B" * (ROOM * 2)
        information = ProgramInformation(title=overlong, artist=overlong, copyright=overlong)
        assert {
            information.title,
            information.artist,
            information.copyright,
        } == {overlong}

    def test_every_line_is_fitted_to_the_room_a_file_gives_it(self) -> None:
        overlong = "B" * (ROOM * 2)
        fitted = ProgramInformation(title=overlong, artist=overlong, copyright=overlong).fitted(BYTE_LINE)
        assert {
            fitted.title,
            fitted.artist,
            fitted.copyright,
        } == {BYTE_LINE.fit(overlong)}

    def test_text_that_fits_is_carried_whole(self) -> None:
        information = ProgramInformation(title=SHORT_TEXT, artist=SHORT_TEXT, copyright=SHORT_TEXT)
        assert information.fitted(BYTE_LINE) == information
