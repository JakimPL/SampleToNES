from dataclasses import dataclass
from typing import Final, Tuple

import pytest
from pydantic import ValidationError

from sampletones_player.specification.screen import COLORS_PER_PALETTE, TILE_SIDE
from sampletones_tools.player.graphics.sheet.drawing import INK, PAPER, Drawing
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

INK_ROW: Final[str] = INK * TILE_SIDE
PAPER_ROW: Final[str] = PAPER * TILE_SIDE
MIXED_ROW: Final[str] = (INK + PAPER) * (TILE_SIDE // 2)
LITERAL_ROWS: Final[Tuple[str, ...]] = tuple(str(color) * TILE_SIDE for color in range(COLORS_PER_PALETTE))
ROWS: Final[Tuple[str, ...]] = (INK_ROW, PAPER_ROW, *LITERAL_ROWS, MIXED_ROW, PAPER_ROW)
BLOCK: Final[str] = "\n".join(ROWS) + "\n"

UNKNOWN_SYMBOL: Final[str] = "x"
COLOR_PAST_THE_PALETTE: Final[str] = str(COLORS_PER_PALETTE)
SHAPE_REFUSAL: Final[str] = "rows of"
SYMBOL_REFUSAL: Final[str] = "spelled in"


class TestADrawingStatedAsABlockOfText(BaseTestSuite):
    def test_every_line_becomes_a_row(self) -> None:
        assert Drawing.model_validate(BLOCK).rows == ROWS

    def test_the_block_reads_as_the_rows_stated_outright(self) -> None:
        assert Drawing.model_validate(BLOCK) == Drawing(rows=ROWS)

    def test_the_tile_is_eight_rows_of_eight_symbols(self) -> None:
        rows = Drawing.model_validate(BLOCK).rows

        assert [len(row) for row in rows] == [TILE_SIDE] * TILE_SIDE


class TestADrawingTheModelRefuses(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        rows: Tuple[str, ...]
        expected: str

    test_cases = (
        TestCase(rows=ROWS[:-1], expected=SHAPE_REFUSAL, label="a row short"),
        TestCase(rows=(*ROWS, PAPER_ROW), expected=SHAPE_REFUSAL, label="a row over"),
        TestCase(rows=(), expected=SHAPE_REFUSAL, label="no rows at all"),
        TestCase(rows=(INK_ROW[:-1], *ROWS[1:]), expected=SHAPE_REFUSAL, label="a row one symbol short"),
        TestCase(rows=(INK_ROW + INK, *ROWS[1:]), expected=SHAPE_REFUSAL, label="a row one symbol long"),
        TestCase(
            rows=(UNKNOWN_SYMBOL * TILE_SIDE, *ROWS[1:]),
            expected=SYMBOL_REFUSAL,
            label="a symbol outside the alphabet",
        ),
        TestCase(
            rows=(COLOR_PAST_THE_PALETTE * TILE_SIDE, *ROWS[1:]),
            expected=SYMBOL_REFUSAL,
            label="a color past the palette",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_rows_are_refused(self, test_case: TestCase) -> None:
        with pytest.raises(ValidationError, match=test_case.expected):
            Drawing(rows=test_case.rows)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_block_stating_them_is_refused(self, test_case: TestCase) -> None:
        with pytest.raises(ValidationError, match=test_case.expected):
            Drawing.model_validate("\n".join(test_case.rows))


class TestTheColorsADrawingTakes(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        ink: int
        paper: int

    test_cases = (
        TestCase(ink=1, paper=0, label="ink over an empty paper"),
        TestCase(ink=3, paper=1, label="ink over a colored paper"),
        TestCase(ink=0, paper=3, label="an empty ink over a colored paper"),
        TestCase(ink=2, paper=2, label="ink and paper of one color"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_ink_and_the_paper_take_the_colors_stated(self, test_case: TestCase) -> None:
        pixels = Drawing(rows=ROWS).pixels(ink=test_case.ink, paper=test_case.paper)

        assert pixels[ROWS.index(INK_ROW)] == (test_case.ink,) * TILE_SIDE
        assert pixels[ROWS.index(PAPER_ROW)] == (test_case.paper,) * TILE_SIDE
        assert pixels[ROWS.index(MIXED_ROW)] == (test_case.ink, test_case.paper) * (TILE_SIDE // 2)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_digit_stays_the_palette_entry_it_names(self, test_case: TestCase) -> None:
        pixels = Drawing(rows=ROWS).pixels(ink=test_case.ink, paper=test_case.paper)

        for color, row in enumerate(LITERAL_ROWS):
            assert pixels[ROWS.index(row)] == (color,) * TILE_SIDE

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_pixels_keep_the_shape_of_the_tile(self, test_case: TestCase) -> None:
        pixels = Drawing(rows=ROWS).pixels(ink=test_case.ink, paper=test_case.paper)

        assert [len(row) for row in pixels] == [TILE_SIDE] * TILE_SIDE
