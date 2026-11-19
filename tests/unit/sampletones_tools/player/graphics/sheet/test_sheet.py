from dataclasses import dataclass
from typing import Dict, Final, Set, Tuple

import pytest
from pydantic import ValidationError

from sampletones_player.specification.screen import (
    COLORS_PER_PALETTE,
    FIRST_GLYPH,
    LAST_GLYPH,
    TILE_SIDE,
    TILES_PER_TABLE,
)
from sampletones_tools.player.graphics.layout.screen import TEXT_GROUP
from sampletones_tools.player.graphics.sheet.drawing import INK, PAPER, Drawing, Pixels
from sampletones_tools.player.graphics.sheet.font import Font
from sampletones_tools.player.graphics.sheet.groups import PatternTable, SheetGroups, TileGroup
from sampletones_tools.player.graphics.sheet.shapes import Shapes
from sampletones_tools.player.graphics.sheet.sheet import TileSheet
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

DOT: Final[str] = "dot"
DASH: Final[str] = "dash"
LETTERS: Final[str] = "AB"
ABSENT_SHAPE: Final[str] = "absent"
ABSENT_GROUP: Final[str] = "nowhere"
UNDRAWN_CHARACTER: Final[str] = "é"
REFUSAL: Final[str] = "which nothing draws"

DRAWINGS: Final[Dict[str, Drawing]] = {
    DOT: Drawing(rows=tuple(INK * TILE_SIDE if row == 0 else PAPER * TILE_SIDE for row in range(TILE_SIDE))),
    DASH: Drawing(rows=tuple((INK + PAPER) * (TILE_SIDE // 2) for _ in range(TILE_SIDE))),
}
LETTER_GROUP: Final[TileGroup] = TileGroup(
    name="letters", first=0x10, ink=3, paper=0, characters=LETTERS, shapes=(DOT,)
)
MARK_GROUP: Final[TileGroup] = TileGroup(name="marks", first=0x80, ink=1, paper=2, shapes=(DOT, DASH))
PIN_GROUP: Final[TileGroup] = TileGroup(name="pins", first=0x01, ink=2, paper=0, shapes=(DASH,))
GROUPS: Final[SheetGroups] = SheetGroups(background=(LETTER_GROUP, MARK_GROUP), sprites=(PIN_GROUP,))
EMPTY: Final[Pixels] = ((0,) * TILE_SIDE,) * TILE_SIDE


@dataclass(frozen=True, kw_only=True)
class TableCase(BaseRegularTestCase):
    table: PatternTable


TABLE_CASES: Final[Tuple[TableCase, ...]] = (
    TableCase(table=PatternTable.BACKGROUND, label="the background table"),
    TableCase(table=PatternTable.SPRITES, label="the sprite table"),
)


def taken_tiles(sheet: TileSheet, table: PatternTable) -> Set[int]:
    return {tile for group in sheet.table(table).values() for tile in group.tiles}


@pytest.fixture(name="font", scope="module")
def font_fixture() -> Font:
    return Font.load()


@pytest.fixture(name="sheet")
def sheet_fixture(font: Font) -> TileSheet:
    """A sheet of two background groups and one sprite group, lettered in the shipped font."""
    return TileSheet(font=font, shapes=Shapes(shapes=DRAWINGS), groups=GROUPS)


class TestWhereASheetPlacesItsTiles(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        table: PatternTable
        group: TileGroup

    test_cases = (
        TestCase(table=PatternTable.BACKGROUND, group=LETTER_GROUP, label="characters and a shape"),
        TestCase(table=PatternTable.BACKGROUND, group=MARK_GROUP, label="shapes alone"),
        TestCase(table=PatternTable.SPRITES, group=PIN_GROUP, label="a group of the sprite table"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_member_stands_where_its_group_places_it(self, test_case: TestCase, sheet: TileSheet) -> None:
        placed = [sheet.tile(test_case.table, test_case.group.name, member) for member in test_case.group.members]

        assert placed == list(test_case.group.tiles)

    def test_each_table_answers_with_its_own_groups_by_name(self, sheet: TileSheet) -> None:
        assert sheet.table(PatternTable.BACKGROUND) == {LETTER_GROUP.name: LETTER_GROUP, MARK_GROUP.name: MARK_GROUP}
        assert sheet.table(PatternTable.SPRITES) == {PIN_GROUP.name: PIN_GROUP}

    def test_a_shape_two_groups_hold_takes_a_tile_in_each(self, sheet: TileSheet) -> None:
        first = sheet.tile(PatternTable.BACKGROUND, LETTER_GROUP.name, DOT)
        second = sheet.tile(PatternTable.BACKGROUND, MARK_GROUP.name, DOT)

        assert (first, second) == (LETTER_GROUP.tile(DOT), MARK_GROUP.tile(DOT))
        assert first != second

    def test_a_group_the_table_lacks_is_a_key_error(self, sheet: TileSheet) -> None:
        with pytest.raises(KeyError):
            sheet.tile(PatternTable.BACKGROUND, ABSENT_GROUP, DOT)

    def test_a_group_of_the_other_table_is_a_key_error(self, sheet: TileSheet) -> None:
        with pytest.raises(KeyError):
            sheet.tile(PatternTable.SPRITES, MARK_GROUP.name, DOT)

    def test_a_member_the_group_lacks_is_a_key_error(self, sheet: TileSheet) -> None:
        with pytest.raises(KeyError):
            sheet.tile(PatternTable.BACKGROUND, MARK_GROUP.name, ABSENT_SHAPE)


class TestTheTilesASheetDraws(BaseTestSuite):
    test_cases = TABLE_CASES

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_table_is_drawn_whole(self, test_case: TableCase, sheet: TileSheet) -> None:
        assert len(sheet.drawn(test_case.table)) == TILES_PER_TABLE

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_tile_no_group_takes_is_left_empty(self, test_case: TableCase, sheet: TileSheet) -> None:
        drawn = sheet.drawn(test_case.table)
        free = set(range(TILES_PER_TABLE)) - taken_tiles(sheet, test_case.table)

        assert all(drawn[tile] == EMPTY for tile in free)

    def test_a_character_is_drawn_in_the_colors_of_its_group(self, sheet: TileSheet, font: Font) -> None:
        drawn = sheet.drawn(PatternTable.BACKGROUND)

        for character in LETTERS:
            expected = font.glyph(character).pixels(ink=LETTER_GROUP.ink, paper=LETTER_GROUP.paper)
            assert drawn[LETTER_GROUP.tile(character)] == expected

    def test_a_shape_takes_the_colors_of_each_group_holding_it(self, sheet: TileSheet) -> None:
        drawn = sheet.drawn(PatternTable.BACKGROUND)

        for group in (LETTER_GROUP, MARK_GROUP):
            assert drawn[group.tile(DOT)] == DRAWINGS[DOT].pixels(ink=group.ink, paper=group.paper)

        assert drawn[LETTER_GROUP.tile(DOT)] != drawn[MARK_GROUP.tile(DOT)]

    def test_a_sprite_group_is_drawn_into_the_sprite_table_alone(self, sheet: TileSheet) -> None:
        expected = DRAWINGS[DASH].pixels(ink=PIN_GROUP.ink, paper=PIN_GROUP.paper)

        assert sheet.drawn(PatternTable.SPRITES)[PIN_GROUP.tile(DASH)] == expected
        assert sheet.drawn(PatternTable.BACKGROUND)[PIN_GROUP.tile(DASH)] == EMPTY


class TestASheetTheModelRefuses(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        characters: str
        shapes: Tuple[str, ...]

    test_cases = (
        TestCase(characters=UNDRAWN_CHARACTER, shapes=(), label="a character the font leaves out"),
        TestCase(characters="", shapes=(ABSENT_SHAPE,), label="a shape nothing draws"),
        TestCase(characters=LETTERS, shapes=(DOT, ABSENT_SHAPE), label="one undrawn member among drawn ones"),
    )

    @staticmethod
    def naming(test_case: TestCase) -> TileGroup:
        return MARK_GROUP.model_copy(update={"characters": test_case.characters, "shapes": test_case.shapes})

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_background_group_naming_it_is_refused(self, test_case: TestCase, font: Font) -> None:
        groups = SheetGroups(background=(self.naming(test_case),), sprites=())

        with pytest.raises(ValidationError, match=REFUSAL):
            TileSheet(font=font, shapes=Shapes(shapes=DRAWINGS), groups=groups)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_sprite_group_naming_it_is_refused(self, test_case: TestCase, font: Font) -> None:
        groups = SheetGroups(background=(), sprites=(self.naming(test_case),))

        with pytest.raises(ValidationError, match=REFUSAL):
            TileSheet(font=font, shapes=Shapes(shapes=DRAWINGS), groups=groups)


class TestTheShippedSheet(BaseTestSuite):
    test_cases = TABLE_CASES

    def test_the_text_group_places_every_printable_character_at_its_own_code(self, shipped_sheet: TileSheet) -> None:
        """The exporter writes text as character codes, so a code is the tile that draws it."""
        codes = range(FIRST_GLYPH, LAST_GLYPH + 1)

        placed = [shipped_sheet.tile(PatternTable.BACKGROUND, TEXT_GROUP, chr(code)) for code in codes]

        assert placed == list(codes)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_table_draws_256_tiles_of_palette_entries(self, test_case: TableCase, shipped_sheet: TileSheet) -> None:
        drawn = shipped_sheet.drawn(test_case.table)
        entries = {entry for tile in drawn for row in tile for entry in row}

        assert len(drawn) == TILES_PER_TABLE
        assert entries <= set(range(COLORS_PER_PALETTE))

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_tile_outside_every_group_is_empty(self, test_case: TableCase, shipped_sheet: TileSheet) -> None:
        drawn = shipped_sheet.drawn(test_case.table)
        free = set(range(TILES_PER_TABLE)) - taken_tiles(shipped_sheet, test_case.table)

        assert all(drawn[tile] == EMPTY for tile in free)
