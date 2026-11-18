from dataclasses import dataclass
from typing import Dict, Final, Union

import pytest
from pydantic import ValidationError

from sampletones_player.specification.screen import PALETTES_PER_LAYER
from sampletones_tools.player.graphics.layout.cells import LAST_COLUMN, LAST_ROW
from sampletones_tools.player.graphics.layout.labels import SpriteLabel
from sampletones_tools.player.graphics.layout.screen import ScreenLayout
from sampletones_tools.player.graphics.sheet.groups import PatternTable
from sampletones_tools.player.graphics.sheet.sheet import TileSheet
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

LabelValue = Union[int, str]

ROW: Final[int] = 7
COLUMN: Final[int] = 2
GROUP: Final[str] = "captions"
TEXT: Final[str] = "Title:"
LAST_PALETTE: Final[int] = PALETTES_PER_LAYER - 1

STATED: Final[Dict[str, LabelValue]] = {
    "row": ROW,
    "column": COLUMN,
    "group": GROUP,
    "text": TEXT,
    "palette": LAST_PALETTE,
}


class TestASpriteLabel(BaseTestSuite):
    def test_it_is_held_as_stated(self) -> None:
        assert SpriteLabel.model_validate(STATED).model_dump() == STATED

    def test_the_first_sprite_palette_is_accepted(self) -> None:
        assert SpriteLabel.model_validate({**STATED, "palette": 0}).palette == 0


class TestALabelTheModelRefuses(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        changes: Dict[str, LabelValue]
        expected: str

    test_cases = (
        TestCase(changes={"row": LAST_ROW + 1}, expected="row", label="a label below the screen"),
        TestCase(changes={"column": LAST_COLUMN + 1}, expected="column", label="a label right of the screen"),
        TestCase(changes={"text": ""}, expected="text", label="a label of no characters"),
        TestCase(changes={"palette": PALETTES_PER_LAYER}, expected="palette", label="a palette past the last"),
        TestCase(changes={"palette": -1}, expected="palette", label="a palette before the first"),
        TestCase(changes={"unnamed": ROW}, expected="unnamed", label="a field the model does not name"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_refusal_names_the_field(self, test_case: TestCase) -> None:
        with pytest.raises(ValidationError, match=test_case.expected):
            SpriteLabel.model_validate({**STATED, **test_case.changes})


class TestTheLabelsOfTheShippedScreen(BaseTestSuite):
    def test_the_sprite_table_draws_every_character_of_every_label(
        self,
        shipped_layout: ScreenLayout,
        shipped_sheet: TileSheet,
    ) -> None:
        sprites = shipped_sheet.table(PatternTable.SPRITES)

        undrawn = [
            (label.text, character)
            for label in shipped_layout.labels
            for character in label.text
            if character not in sprites[label.group].characters
        ]

        assert not undrawn

    def test_every_label_ends_on_the_screen(self, shipped_layout: ScreenLayout) -> None:
        assert all(label.column + len(label.text) - 1 <= LAST_COLUMN for label in shipped_layout.labels)
