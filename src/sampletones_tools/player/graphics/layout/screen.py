from __future__ import annotations

from typing import Final, Tuple

from pydantic import BaseModel, ConfigDict, model_validator

from sampletones_player.specification.screen import (
    ATTRIBUTE_CELL_TILES,
    ATTRIBUTE_CELLS_PER_BYTE,
    ATTRIBUTE_COLUMNS,
    ATTRIBUTE_ROWS,
    ATTRIBUTE_TABLE_SIDE,
    COLOR_BITS,
    NAMETABLE_SIZE,
    PALETTES_PER_LAYER,
    SCREEN_COLUMNS,
    SPRITES_PER_SCANLINE,
)
from sampletones_shared.utils.serialization import load_yaml_model
from sampletones_tools.player.graphics.layout.cells import LAST_COLUMN, LAST_ROW
from sampletones_tools.player.graphics.layout.elements import Element
from sampletones_tools.player.graphics.layout.fields import (
    ChannelFields,
    KeyboardFields,
    ProgramFields,
    ProgressField,
    TransportFields,
)
from sampletones_tools.player.graphics.layout.labels import SpriteLabel
from sampletones_tools.player.graphics.layout.palettes import Palettes
from sampletones_tools.player.graphics.paths import SCREEN_PATH
from sampletones_tools.player.graphics.sheet.groups import PatternTable
from sampletones_tools.player.graphics.sheet.sheet import TileSheet

TEXT_GROUP: Final[str] = "plain"
EMPTY_CELL: Final[str] = " "


class ScreenLayout(BaseModel):
    """The player screen as data: what it always shows, its colors, and where the song is written.

    Attributes:
        palettes: The colors of the background and of the sprites.
        attributes: The background palette of each 16-pixel square of cells, a digit per square.
        elements: What the screen always shows, later elements drawn over earlier ones.
        labels: The fixed texts drawn with sprites.
        program: Where the program's text is written.
        transport: Where the playing state and the times are written.
        progress: Where the progress bar lies.
        channels: Where each channel's readings are written.
        keyboard: Where the keyboard and its markers lie.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    palettes: Palettes
    attributes: Tuple[str, ...]
    elements: Tuple[Element, ...]
    labels: Tuple[SpriteLabel, ...]
    program: ProgramFields
    transport: TransportFields
    progress: ProgressField
    channels: ChannelFields
    keyboard: KeyboardFields

    @model_validator(mode="before")
    @classmethod
    def _read_the_attribute_rows(cls, value: object) -> object:
        if isinstance(value, dict) and isinstance(value.get("attributes"), str):
            return {**value, "attributes": tuple(value["attributes"].split())}

        return value

    @model_validator(mode="after")
    def _validate_the_attributes_cover_the_screen(self) -> ScreenLayout:
        if len(self.attributes) != ATTRIBUTE_ROWS or any(len(row) != ATTRIBUTE_COLUMNS for row in self.attributes):
            raise ValueError(f"the attributes take {ATTRIBUTE_ROWS} rows of {ATTRIBUTE_COLUMNS} palette digits")

        digits = {digit for row in self.attributes for digit in row}
        if not digits <= {str(palette) for palette in range(PALETTES_PER_LAYER)}:
            raise ValueError(f"an attribute names one of the {PALETTES_PER_LAYER} background palettes")

        return self

    @model_validator(mode="after")
    def _validate_the_labels_fit_their_scanlines(self) -> ScreenLayout:
        for row in {label.row for label in self.labels}:
            sprites = sum(len(label.text) for label in self.labels if label.row == row)
            if sprites > SPRITES_PER_SCANLINE:
                raise ValueError(
                    f"the labels on row {row} take {sprites} sprites, and a scanline shows {SPRITES_PER_SCANLINE}"
                )

        return self

    @classmethod
    def load(cls) -> ScreenLayout:
        """The layout the package ships."""
        return load_yaml_model(SCREEN_PATH, cls)

    def nametable(self, sheet: TileSheet) -> bytes:
        """The tile every cell shows before a song is written over it.

        Args:
            sheet: The tiles the elements name.

        Returns:
            bytes: One tile per cell, row by row.

        Raises:
            KeyError: If an element names a group or a member the sheet holds no tile for.
            ValueError: If an element reaches past the screen's edge.
        """
        cells = bytearray([sheet.tile(PatternTable.BACKGROUND, TEXT_GROUP, EMPTY_CELL)] * NAMETABLE_SIZE)
        for element in self.elements:
            for row, column, tile in element.cells(sheet):
                if row > LAST_ROW or column > LAST_COLUMN:
                    raise ValueError(f"an element reaches row {row}, column {column}, past the screen's edge")

                cells[row * SCREEN_COLUMNS + column] = tile

        return bytes(cells)

    def palette_at(self, row: int, column: int) -> int:
        """The background palette the cell at ``row`` and ``column`` is drawn in."""
        return int(self.attributes[row // ATTRIBUTE_CELL_TILES][column // ATTRIBUTE_CELL_TILES])

    def attribute_table(self) -> bytes:
        """The attribute memory: each byte packs the palettes of four neighboring squares.

        A byte covers a block four cells wide and four tall. Its two low bits color the top left
        square, the next two the top right, then the bottom left and the bottom right. The screen
        is thirty cells tall, so the last row of bytes covers two rows of cells and leaves its
        upper bits at zero.

        Returns:
            bytes: The 64 attribute bytes, row by row.
        """
        table = bytearray()
        for byte_row in range(ATTRIBUTE_TABLE_SIDE):
            for byte_column in range(ATTRIBUTE_TABLE_SIDE):
                packed = 0
                for square in range(ATTRIBUTE_CELLS_PER_BYTE * ATTRIBUTE_CELLS_PER_BYTE):
                    row = byte_row * ATTRIBUTE_CELLS_PER_BYTE + square // ATTRIBUTE_CELLS_PER_BYTE
                    column = byte_column * ATTRIBUTE_CELLS_PER_BYTE + square % ATTRIBUTE_CELLS_PER_BYTE
                    if row < ATTRIBUTE_ROWS:
                        packed |= int(self.attributes[row][column]) << (square * COLOR_BITS)

                table.append(packed)

        return bytes(table)
