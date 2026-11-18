from dataclasses import dataclass
from typing import Dict, Final, Tuple

import pytest
from pydantic import ValidationError

from sampletones_player.specification.screen import FIRST_GLYPH, GLYPH_COUNT, LAST_GLYPH
from sampletones_tools.player.graphics.sheet.drawing import Drawing
from sampletones_tools.player.graphics.sheet.font import Font
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

PRINTABLE: Final[range] = range(FIRST_GLYPH, LAST_GLYPH + 1)
BEFORE_THE_FIRST: Final[int] = FIRST_GLYPH - 1
AFTER_THE_LAST: Final[int] = LAST_GLYPH + 1
ACCENTED_CODE: Final[int] = 0xE9
REFUSAL: Final[str] = "each once"


@pytest.fixture(name="font", scope="module")
def font_fixture() -> Font:
    return Font.load()


class TestTheShippedFont(BaseTestSuite):
    def test_it_draws_exactly_the_printable_characters(self, font: Font) -> None:
        assert set(font.glyphs) == set(PRINTABLE)

    def test_it_holds_a_glyph_for_each_of_the_glyphs_the_screen_counts(self, font: Font) -> None:
        assert len(font.glyphs) == GLYPH_COUNT

    def test_it_starts_at_the_first_printable_character(self, font: Font) -> None:
        assert font.first == FIRST_GLYPH

    def test_every_printable_character_is_drawn(self, font: Font) -> None:
        assert all(font.draws(chr(code)) for code in PRINTABLE)

    def test_a_glyph_is_the_drawing_held_at_the_character_code(self, font: Font) -> None:
        assert all(font.glyph(chr(code)) == font.glyphs[code] for code in PRINTABLE)


class TestACharacterOutsideTheFont(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        code: int

    test_cases = (
        TestCase(code=BEFORE_THE_FIRST, label="the code before the first glyph"),
        TestCase(code=AFTER_THE_LAST, label="the code after the last glyph"),
        TestCase(code=ACCENTED_CODE, label="an accented letter"),
        TestCase(code=ord("\n"), label="a line break"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_font_says_it_draws_no_such_character(self, test_case: TestCase, font: Font) -> None:
        assert not font.draws(chr(test_case.code))

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_asking_for_its_glyph_is_a_key_error(self, test_case: TestCase, font: Font) -> None:
        with pytest.raises(KeyError):
            font.glyph(chr(test_case.code))


class TestAFontTheModelRefuses(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        first: int
        dropped: Tuple[int, ...]
        added: Tuple[int, ...]

    test_cases = (
        TestCase(first=FIRST_GLYPH, dropped=(LAST_GLYPH,), added=(), label="a printable character left out"),
        TestCase(first=FIRST_GLYPH, dropped=(), added=(AFTER_THE_LAST,), label="a character past the last"),
        TestCase(first=FIRST_GLYPH, dropped=(), added=(BEFORE_THE_FIRST,), label="a character before the first"),
        TestCase(first=FIRST_GLYPH + 1, dropped=(), added=(), label="another first character"),
        TestCase(
            first=FIRST_GLYPH + 1,
            dropped=(FIRST_GLYPH,),
            added=(AFTER_THE_LAST,),
            label="the whole range moved by one",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_refusal_names_the_characters_a_font_draws(self, test_case: TestCase, font: Font) -> None:
        glyphs: Dict[int, Drawing] = {
            code: drawing for code, drawing in font.glyphs.items() if code not in test_case.dropped
        }
        glyphs.update({code: font.glyphs[FIRST_GLYPH] for code in test_case.added})

        with pytest.raises(ValidationError, match=REFUSAL):
            Font(first=test_case.first, glyphs=glyphs)
