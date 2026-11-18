from dataclasses import dataclass
from typing import Dict, Final, Tuple, Union

import pytest
from pydantic import ValidationError

from sampletones_player.specification.screen import COLORS_PER_PALETTE, TILES_PER_TABLE
from sampletones_tools.player.graphics.sheet.groups import SheetGroups, TileGroup
from sampletones_tools.player.graphics.sheet.sheet import TileSheet
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

GroupValue = Union[int, str, Tuple[str, ...]]

NAME: Final[str] = "marks"
OTHER_NAME: Final[str] = "letters"
FIRST: Final[int] = 0x40
INK_COLOR: Final[int] = 2
PAPER_COLOR: Final[int] = 1
CHARACTERS: Final[str] = "AB"
SHAPES: Final[Tuple[str, ...]] = ("dot", "dash")
MEMBERS: Final[Tuple[str, ...]] = (*CHARACTERS, *SHAPES)
ABSENT_MEMBER: Final[str] = "absent"
LAST_TILE: Final[int] = TILES_PER_TABLE - 1

STATED: Final[Dict[str, GroupValue]] = {
    "name": NAME,
    "first": FIRST,
    "ink": INK_COLOR,
    "paper": PAPER_COLOR,
    "characters": CHARACTERS,
    "shapes": SHAPES,
}

MEMBER_REFUSAL: Final[str] = "names a member twice"
TABLE_REFUSAL: Final[str] = "runs past"
NAME_REFUSAL: Final[str] = "names each of its tile groups once"
TILE_REFUSAL: Final[str] = "take the same tile"


def group_at(name: str, first: int) -> TileGroup:
    return TileGroup(name=name, first=first, ink=INK_COLOR, paper=PAPER_COLOR, characters=CHARACTERS, shapes=SHAPES)


@pytest.fixture(name="group")
def group_fixture() -> TileGroup:
    return TileGroup.model_validate(STATED)


class TestTheTilesAGroupTakes(BaseTestSuite):
    def test_the_characters_come_first_and_the_shapes_follow(self, group: TileGroup) -> None:
        assert group.members == MEMBERS

    def test_the_run_starts_at_the_first_tile_and_holds_a_tile_per_member(self, group: TileGroup) -> None:
        assert group.tiles == range(FIRST, FIRST + len(MEMBERS))

    def test_every_member_stands_at_its_place_in_the_run(self, group: TileGroup) -> None:
        assert [group.tile(member) for member in MEMBERS] == list(range(FIRST, FIRST + len(MEMBERS)))

    def test_a_member_the_group_lacks_is_a_key_error(self, group: TileGroup) -> None:
        with pytest.raises(KeyError, match=NAME):
            group.tile(ABSENT_MEMBER)

    def test_a_group_of_characters_alone_holds_a_tile_for_each(self) -> None:
        group = TileGroup(name=NAME, first=FIRST, ink=INK_COLOR, paper=PAPER_COLOR, characters=CHARACTERS)

        assert group.members == tuple(CHARACTERS)

    def test_a_group_of_shapes_alone_holds_a_tile_for_each(self) -> None:
        group = TileGroup(name=NAME, first=FIRST, ink=INK_COLOR, paper=PAPER_COLOR, shapes=SHAPES)

        assert group.members == SHAPES

    def test_a_group_may_end_at_the_last_tile_of_its_table(self) -> None:
        group = group_at(NAME, TILES_PER_TABLE - len(MEMBERS))

        assert group.tile(MEMBERS[-1]) == LAST_TILE


class TestAGroupTheModelRefuses(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        changes: Dict[str, GroupValue]
        expected: str

    test_cases = (
        TestCase(changes={"characters": "AA"}, expected=MEMBER_REFUSAL, label="a character spelled twice"),
        TestCase(changes={"shapes": ("dot", "dot")}, expected=MEMBER_REFUSAL, label="a shape named twice"),
        TestCase(changes={"shapes": ("A",)}, expected=MEMBER_REFUSAL, label="a shape named as a character is"),
        TestCase(changes={"first": LAST_TILE}, expected=TABLE_REFUSAL, label="a run past the end of the table"),
        TestCase(changes={"first": TILES_PER_TABLE}, expected="first", label="a first tile past the table"),
        TestCase(changes={"first": -1}, expected="first", label="a first tile before the table"),
        TestCase(changes={"ink": COLORS_PER_PALETTE}, expected="ink", label="an ink past the palette"),
        TestCase(changes={"paper": COLORS_PER_PALETTE}, expected="paper", label="a paper past the palette"),
        TestCase(changes={"ink": -1}, expected="ink", label="an ink before the palette"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_refusal_names_what_is_wrong(self, test_case: TestCase) -> None:
        with pytest.raises(ValidationError, match=test_case.expected):
            TileGroup.model_validate({**STATED, **test_case.changes})


class TestTheGroupsOfAPatternTable(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        groups: Tuple[TileGroup, ...]
        expected: str

    test_cases = (
        TestCase(
            groups=(group_at(NAME, FIRST), group_at(OTHER_NAME, FIRST)),
            expected=TILE_REFUSAL,
            label="two groups starting at one tile",
        ),
        TestCase(
            groups=(group_at(NAME, FIRST), group_at(OTHER_NAME, FIRST + len(MEMBERS) - 1)),
            expected=TILE_REFUSAL,
            label="a group starting on the last tile of another",
        ),
        TestCase(
            groups=(group_at(NAME, FIRST), group_at(NAME, FIRST + len(MEMBERS))),
            expected=NAME_REFUSAL,
            label="two groups of one name",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_background_table_refuses_them(self, test_case: TestCase) -> None:
        with pytest.raises(ValidationError, match=test_case.expected):
            SheetGroups(background=test_case.groups, sprites=())

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_sprite_table_refuses_them(self, test_case: TestCase) -> None:
        with pytest.raises(ValidationError, match=test_case.expected):
            SheetGroups(background=(), sprites=test_case.groups)

    def test_a_group_may_start_where_another_ends(self) -> None:
        groups = (group_at(NAME, FIRST), group_at(OTHER_NAME, FIRST + len(MEMBERS)))

        assert SheetGroups(background=groups, sprites=()).background == groups

    def test_each_table_names_and_numbers_its_groups_on_its_own(self) -> None:
        groups = SheetGroups(background=(group_at(NAME, FIRST),), sprites=(group_at(NAME, FIRST),))

        assert groups.background == groups.sprites

    def test_the_shipped_sheet_carries_the_groups_the_package_ships(self, shipped_sheet: TileSheet) -> None:
        assert SheetGroups.load() == shipped_sheet.groups
