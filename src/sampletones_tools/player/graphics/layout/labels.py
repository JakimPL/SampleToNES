from typing import Final

from pydantic import BaseModel, ConfigDict, Field

from sampletones_player.specification.screen import PALETTES_PER_LAYER
from sampletones_tools.player.graphics.layout.cells import Column, Row

LAST_PALETTE: Final[int] = PALETTES_PER_LAYER - 1


class SpriteLabel(BaseModel):
    """A short fixed text drawn with sprites, one sprite to a character.

    Sprites take their colors from palettes of their own, so a label stands in a color the cells
    beneath it hold no entry for.

    Attributes:
        row: The row of cells the label lies over.
        column: The cell its first character lies over.
        group: The sprite tile group its characters are drawn from.
        text: The characters, left to right.
        palette: The sprite palette the label takes.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    row: Row
    column: Column
    group: str
    text: str = Field(min_length=1)
    palette: int = Field(ge=0, le=LAST_PALETTE)
