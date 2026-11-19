from typing import Final

import pytest
from pydantic import ValidationError

from sampletones_player.specification.screen import TILE_SIDE
from sampletones_tools.player.graphics.sheet.drawing import INK, PAPER, Drawing
from sampletones_tools.player.graphics.sheet.shapes import Shapes
from sampletones_tools.player.graphics.sheet.sheet import TileSheet
from tests.suite.base import BaseTestSuite

NAME: Final[str] = "stripes"
ROW: Final[str] = (INK + PAPER) * (TILE_SIDE // 2)
BLOCK: Final[str] = "\n".join([ROW] * TILE_SIDE) + "\n"
SHORT_BLOCK: Final[str] = "\n".join([ROW] * (TILE_SIDE - 1)) + "\n"


class TestTheNamedShapes(BaseTestSuite):
    def test_a_shape_stated_as_a_block_of_text_is_read_as_a_drawing(self) -> None:
        shapes = Shapes.model_validate({"shapes": {NAME: BLOCK}})

        assert shapes.shapes == {NAME: Drawing.model_validate(BLOCK)}

    def test_a_shape_drawn_as_another_size_than_a_tile_is_refused(self) -> None:
        with pytest.raises(ValidationError, match=NAME):
            Shapes.model_validate({"shapes": {NAME: SHORT_BLOCK}})

    def test_the_shipped_sheet_carries_the_shapes_the_package_ships(self, shipped_sheet: TileSheet) -> None:
        assert Shapes.load() == shipped_sheet.shapes
