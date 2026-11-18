from itertools import cycle, islice
from typing import Annotated, List, Literal, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field

from sampletones_tools.player.graphics.layout.cells import Cell, Column, Row
from sampletones_tools.player.graphics.sheet.groups import PatternTable
from sampletones_tools.player.graphics.sheet.sheet import TileSheet


class TextElement(BaseModel):
    """A line of text the screen always shows, each character a tile of one group.

    Attributes:
        kind: Marks the element as text.
        row: The row of cells the text lies in.
        column: The cell its first character takes.
        group: The tile group its characters are drawn from.
        text: The characters, left to right.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["text"]
    row: Row
    column: Column
    group: str
    text: str

    def cells(self, sheet: TileSheet) -> List[Cell]:
        """The cells the text fills, as row, column and tile."""
        return [
            (self.row, self.column + offset, sheet.tile(PatternTable.BACKGROUND, self.group, character))
            for offset, character in enumerate(self.text)
        ]


class PatternElement(BaseModel):
    """A block of cells filled by repeating a run of tiles along each of its rows.

    A single member fills the block evenly, and a longer run lays out a figure that repeats, the
    way the keyboard repeats its octave.

    Attributes:
        kind: Marks the element as a pattern.
        row: The block's top row of cells.
        column: The block's leftmost cell.
        width: How many cells each row of the block spans.
        height: How many rows the block spans.
        group: The tile group the members are drawn from.
        members: The run of members a row repeats, left to right.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["pattern"]
    row: Row
    column: Column
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    group: str
    members: Tuple[str, ...] = Field(min_length=1)

    def cells(self, sheet: TileSheet) -> List[Cell]:
        """The cells the block fills, as row, column and tile."""
        tiles = [sheet.tile(PatternTable.BACKGROUND, self.group, member) for member in self.members]
        return [
            (self.row + row, self.column + offset, tile)
            for row in range(self.height)
            for offset, tile in enumerate(islice(cycle(tiles), self.width))
        ]


Element = Annotated[Union[TextElement, PatternElement], Field(discriminator="kind")]
