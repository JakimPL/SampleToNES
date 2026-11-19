from pydantic import BaseModel, ConfigDict, Field

from sampletones_player.specification.binary import MAX_BYTE_VALUE
from sampletones_tools.console.rom.registers import (
    NAMETABLE_ATTRIBUTES,
    NAMETABLE_TILES,
    PALETTE_SIZE,
    SPRITE_MEMORY_SIZE,
)


class Screen(BaseModel):
    """What the picture processor holds for the picture it draws next.

    This is everything a renderer needs beside the cartridge's pattern tables: the nametable the
    scroll selects, the palettes with their shared backdrop entries already folded, and the sprite
    memory as the last transfer left it.

    Attributes:
        nametable: The tile each of the 32 by 30 cells shows, row by row.
        attributes: The palette each 16 by 16 pixel area of that nametable takes, as the processor packs them.
        palette: The four background palettes followed by the four sprite palettes.
        sprites: The 64 sprites, four bytes each: row, tile, attributes, column.
        control: The control register.
        mask: The mask register, whose background and sprite bits switch the drawing on.
        scroll_x: The column of the nametable the picture's left edge stands at, in pixels.
        scroll_y: The row of the nametable the picture's top edge stands at, in pixels.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    nametable: bytes = Field(min_length=NAMETABLE_TILES, max_length=NAMETABLE_TILES)
    attributes: bytes = Field(min_length=NAMETABLE_ATTRIBUTES, max_length=NAMETABLE_ATTRIBUTES)
    palette: bytes = Field(min_length=PALETTE_SIZE, max_length=PALETTE_SIZE)
    sprites: bytes = Field(min_length=SPRITE_MEMORY_SIZE, max_length=SPRITE_MEMORY_SIZE)
    control: int = Field(ge=0, le=MAX_BYTE_VALUE)
    mask: int = Field(ge=0, le=MAX_BYTE_VALUE)
    scroll_x: int = Field(ge=0)
    scroll_y: int = Field(ge=0)
