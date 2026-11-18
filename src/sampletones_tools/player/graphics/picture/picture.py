from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

from sampletones_player.specification.screen import (
    ATTRIBUTE_TABLE_SIZE,
    NAMETABLE_SIZE,
    PALETTE_SIZE,
    SPRITE_MEMORY_SIZE,
)


class Picture(BaseModel):
    """Everything the console's video memory holds for one frame of the screen.

    These are the bytes the hardware keeps, so a picture stated from the layout and one captured
    from a running cartridge compare byte for byte and render through the same code.

    Attributes:
        nametable: The tile each of the 32 by 30 cells shows.
        attributes: The palette each 16-pixel square of cells takes, four squares to a byte.
        palette: The colors of the four background palettes, then of the four sprite palettes.
        sprites: The sprite memory: vertical position, tile, attributes and horizontal position
            for each of the 64 sprites.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    nametable: bytes
    attributes: bytes
    palette: bytes
    sprites: bytes

    @model_validator(mode="after")
    def _validate_every_part_has_its_size(self) -> Picture:
        for name, held, size in (
            ("nametable", self.nametable, NAMETABLE_SIZE),
            ("attributes", self.attributes, ATTRIBUTE_TABLE_SIZE),
            ("palette", self.palette, PALETTE_SIZE),
            ("sprites", self.sprites, SPRITE_MEMORY_SIZE),
        ):
            if len(held) != size:
                raise ValueError(f"a picture's {name} takes {size} bytes, got {len(held)}")

        return self
