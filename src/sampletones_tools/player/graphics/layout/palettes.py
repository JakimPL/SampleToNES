from __future__ import annotations

from typing import Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sampletones_player.specification.screen import MASTER_COLOR_COUNT, PALETTES_PER_LAYER

PaletteColors = Tuple[int, int, int, int]


class Palettes(BaseModel):
    """The colors the screen is drawn in, as entries of the console's own palette.

    Each palette opens with the backdrop, which every background palette shares.

    Attributes:
        background: The four palettes the cells choose from.
        sprites: The four palettes the sprites choose from.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    background: Tuple[PaletteColors, ...] = Field(min_length=PALETTES_PER_LAYER, max_length=PALETTES_PER_LAYER)
    sprites: Tuple[PaletteColors, ...] = Field(min_length=PALETTES_PER_LAYER, max_length=PALETTES_PER_LAYER)

    @model_validator(mode="after")
    def _validate_every_color_exists(self) -> Palettes:
        colors = [color for palette in self.background + self.sprites for color in palette]
        if any(not 0 <= color < MASTER_COLOR_COUNT for color in colors):
            raise ValueError(f"a palette names colors below {MASTER_COLOR_COUNT:#04x}")

        return self

    def to_bytes(self) -> bytes:
        """The palette memory: the background palettes, then the sprite palettes."""
        return bytes(color for palette in self.background + self.sprites for color in palette)
