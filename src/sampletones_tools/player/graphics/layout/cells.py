from typing import Annotated, Final, Tuple

from pydantic import Field

from sampletones_player.specification.screen import SCREEN_COLUMNS, SCREEN_ROWS

LAST_ROW: Final[int] = SCREEN_ROWS - 1
LAST_COLUMN: Final[int] = SCREEN_COLUMNS - 1
Row = Annotated[int, Field(ge=0, le=LAST_ROW)]
Column = Annotated[int, Field(ge=0, le=LAST_COLUMN)]
Cell = Tuple[int, int, int]
