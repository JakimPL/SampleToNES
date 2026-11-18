from dataclasses import dataclass
from typing import Final

import pytest
from pydantic import TypeAdapter, ValidationError

from sampletones_player.specification.screen import SCREEN_COLUMNS, SCREEN_ROWS
from sampletones_tools.player.graphics.layout.cells import LAST_COLUMN, LAST_ROW, Column, Row
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

ROW: Final[TypeAdapter[int]] = TypeAdapter(Row)
COLUMN: Final[TypeAdapter[int]] = TypeAdapter(Column)
FIRST: Final[int] = 0
BEFORE_THE_FIRST: Final[int] = -1


@dataclass(frozen=True, kw_only=True)
class PositionCase(BaseRegularTestCase):
    adapter: TypeAdapter[int]
    position: int


class TestAPositionOnTheScreen(BaseTestSuite):
    test_cases = (
        PositionCase(adapter=ROW, position=FIRST, label="the first row"),
        PositionCase(adapter=ROW, position=LAST_ROW, label="the last row"),
        PositionCase(adapter=COLUMN, position=FIRST, label="the first column"),
        PositionCase(adapter=COLUMN, position=LAST_COLUMN, label="the last column"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_it_is_accepted_as_stated(self, test_case: PositionCase) -> None:
        assert test_case.adapter.validate_python(test_case.position) == test_case.position

    def test_the_last_cell_is_the_corner_of_the_screen(self) -> None:
        assert (LAST_ROW + 1, LAST_COLUMN + 1) == (SCREEN_ROWS, SCREEN_COLUMNS)


class TestAPositionOffTheScreen(BaseTestSuite):
    test_cases = (
        PositionCase(adapter=ROW, position=BEFORE_THE_FIRST, label="a row above the screen"),
        PositionCase(adapter=ROW, position=SCREEN_ROWS, label="a row below the screen"),
        PositionCase(adapter=COLUMN, position=BEFORE_THE_FIRST, label="a column left of the screen"),
        PositionCase(adapter=COLUMN, position=SCREEN_COLUMNS, label="a column right of the screen"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_it_is_refused(self, test_case: PositionCase) -> None:
        with pytest.raises(ValidationError):
            test_case.adapter.validate_python(test_case.position)
