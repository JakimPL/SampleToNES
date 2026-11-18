from dataclasses import dataclass
from typing import Dict, Final, List, Tuple, Type, Union

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from sampletones_tools.player.graphics.layout.cells import LAST_COLUMN, LAST_ROW, Cell
from sampletones_tools.player.graphics.layout.elements import Element, PatternElement, TextElement
from sampletones_tools.player.graphics.layout.screen import TEXT_GROUP
from sampletones_tools.player.graphics.sheet.groups import PatternTable
from sampletones_tools.player.graphics.sheet.sheet import TileSheet
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

ElementValue = Union[int, str, Tuple[str, ...]]

ROW: Final[int] = 5
COLUMN: Final[int] = 7
TEXT: Final[str] = "Play it"
RUN: Final[Tuple[str, ...]] = ("a", "b", "c")
WIDTH: Final[int] = 7
HEIGHT: Final[int] = 2
ABSENT_GROUP: Final[str] = "nowhere"
UNDRAWN_CHARACTER: Final[str] = "é"

TEXT_STATED: Final[Dict[str, ElementValue]] = {
    "kind": "text",
    "row": ROW,
    "column": COLUMN,
    "group": TEXT_GROUP,
    "text": TEXT,
}
PATTERN_STATED: Final[Dict[str, ElementValue]] = {
    "kind": "pattern",
    "row": ROW,
    "column": COLUMN,
    "width": WIDTH,
    "height": HEIGHT,
    "group": TEXT_GROUP,
    "members": RUN,
}
ELEMENT: Final[TypeAdapter[Union[TextElement, PatternElement]]] = TypeAdapter(Element)


def text_tiles(sheet: TileSheet, members: Tuple[str, ...]) -> List[int]:
    return [sheet.tile(PatternTable.BACKGROUND, TEXT_GROUP, member) for member in members]


def rows_of(cells: List[Cell]) -> List[int]:
    return [row for row, _, _ in cells]


def columns_of(cells: List[Cell]) -> List[int]:
    return [column for _, column, _ in cells]


def tiles_of(cells: List[Cell]) -> List[int]:
    return [tile for _, _, tile in cells]


class TestTheCellsATextFills(BaseTestSuite):
    def test_every_character_takes_the_next_cell_of_the_row(self, shipped_sheet: TileSheet) -> None:
        cells = TextElement.model_validate(TEXT_STATED).cells(shipped_sheet)

        assert rows_of(cells) == [ROW] * len(TEXT)
        assert columns_of(cells) == list(range(COLUMN, COLUMN + len(TEXT)))

    def test_every_cell_shows_the_tile_its_group_draws_the_character_with(self, shipped_sheet: TileSheet) -> None:
        cells = TextElement.model_validate(TEXT_STATED).cells(shipped_sheet)

        assert tiles_of(cells) == text_tiles(shipped_sheet, tuple(TEXT))

    def test_a_text_of_no_characters_fills_no_cell(self, shipped_sheet: TileSheet) -> None:
        assert not TextElement.model_validate({**TEXT_STATED, "text": ""}).cells(shipped_sheet)

    def test_a_character_the_group_lacks_is_a_key_error(self, shipped_sheet: TileSheet) -> None:
        element = TextElement.model_validate({**TEXT_STATED, "text": UNDRAWN_CHARACTER})

        with pytest.raises(KeyError):
            element.cells(shipped_sheet)

    def test_a_group_the_sheet_lacks_is_a_key_error(self, shipped_sheet: TileSheet) -> None:
        element = TextElement.model_validate({**TEXT_STATED, "group": ABSENT_GROUP})

        with pytest.raises(KeyError):
            element.cells(shipped_sheet)


class TestTheCellsAPatternFills(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        members: Tuple[str, ...]
        width: int
        height: int
        expected: Tuple[str, ...]

    test_cases = (
        TestCase(members=("a",), width=3, height=1, expected=("a", "a", "a"), label="one member along a row"),
        TestCase(
            members=("a",),
            width=2,
            height=3,
            expected=("a", "a", "a", "a", "a", "a"),
            label="one member over a block",
        ),
        TestCase(
            members=RUN,
            width=7,
            height=1,
            expected=("a", "b", "c", "a", "b", "c", "a"),
            label="a run repeated along the width",
        ),
        TestCase(
            members=RUN,
            width=4,
            height=2,
            expected=("a", "b", "c", "a", "a", "b", "c", "a"),
            label="a run started anew on every row",
        ),
        TestCase(members=RUN, width=2, height=1, expected=("a", "b"), label="a run cut at the width"),
        TestCase(members=RUN, width=3, height=1, expected=RUN, label="a run exactly as wide as the block"),
    )

    @staticmethod
    def element(test_case: TestCase) -> PatternElement:
        return PatternElement.model_validate(
            {**PATTERN_STATED, "members": test_case.members, "width": test_case.width, "height": test_case.height}
        )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_run_repeats_along_every_row(self, test_case: TestCase, shipped_sheet: TileSheet) -> None:
        cells = self.element(test_case).cells(shipped_sheet)

        assert tiles_of(cells) == text_tiles(shipped_sheet, test_case.expected)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_block_is_filled_row_by_row_from_its_top_left_cell(
        self,
        test_case: TestCase,
        shipped_sheet: TileSheet,
    ) -> None:
        cells = self.element(test_case).cells(shipped_sheet)

        expected = [
            (ROW + row, COLUMN + offset) for row in range(test_case.height) for offset in range(test_case.width)
        ]
        assert list(zip(rows_of(cells), columns_of(cells))) == expected

    def test_a_member_the_group_lacks_is_a_key_error(self, shipped_sheet: TileSheet) -> None:
        element = PatternElement.model_validate({**PATTERN_STATED, "members": (UNDRAWN_CHARACTER,)})

        with pytest.raises(KeyError):
            element.cells(shipped_sheet)


class TestAnElementTheModelRefuses(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        model: Type[BaseModel]
        stated: Dict[str, ElementValue]
        expected: str

    test_cases = (
        TestCase(
            model=TextElement,
            stated={**TEXT_STATED, "row": LAST_ROW + 1},
            expected="row",
            label="a text below the screen",
        ),
        TestCase(
            model=TextElement,
            stated={**TEXT_STATED, "column": LAST_COLUMN + 1},
            expected="column",
            label="a text right of the screen",
        ),
        TestCase(
            model=PatternElement,
            stated={**PATTERN_STATED, "row": LAST_ROW + 1},
            expected="row",
            label="a pattern below the screen",
        ),
        TestCase(
            model=PatternElement,
            stated={**PATTERN_STATED, "column": LAST_COLUMN + 1},
            expected="column",
            label="a pattern right of the screen",
        ),
        TestCase(
            model=PatternElement,
            stated={**PATTERN_STATED, "width": 0},
            expected="width",
            label="a pattern of no width",
        ),
        TestCase(
            model=PatternElement,
            stated={**PATTERN_STATED, "height": 0},
            expected="height",
            label="a pattern of no height",
        ),
        TestCase(
            model=PatternElement,
            stated={**PATTERN_STATED, "members": ()},
            expected="members",
            label="a pattern of no members",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_refusal_names_the_field(self, test_case: TestCase) -> None:
        with pytest.raises(ValidationError, match=test_case.expected):
            test_case.model.model_validate(test_case.stated)


class TestAnElementReadByItsKind(BaseTestSuite):
    def test_a_text_is_read_as_a_text(self) -> None:
        assert ELEMENT.validate_python(TEXT_STATED) == TextElement.model_validate(TEXT_STATED)

    def test_a_pattern_is_read_as_a_pattern(self) -> None:
        assert ELEMENT.validate_python(PATTERN_STATED) == PatternElement.model_validate(PATTERN_STATED)

    def test_another_kind_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="kind"):
            ELEMENT.validate_python({**TEXT_STATED, "kind": "picture"})
