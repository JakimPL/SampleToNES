from __future__ import annotations

from typing import Final, Tuple

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, model_validator

from sampletones_player.specification.screen import MASTER_COLOR_COUNT
from sampletones_shared.utils.serialization import load_yaml_model
from sampletones_tools.player.graphics.paths import COLORS_PATH

HEX_PREFIX: Final[str] = "#"
HEX_BASE: Final[int] = 16
CHANNEL_DIGITS: Final[int] = 2
CHANNEL_COUNT: Final[int] = 3


class MasterPalette(BaseModel):
    """The colors the console can show, as one common display renders them.

    The console states a color as a number and leaves its look to the television, so these values
    serve previews and comparisons alone and never reach a cartridge.

    Attributes:
        colors: The 64 colors as hexadecimal triplets, in rows of the console's own numbering.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    colors: Tuple[Tuple[str, ...], ...]

    @model_validator(mode="after")
    def _validate_every_color_is_stated(self) -> MasterPalette:
        stated = sum(len(row) for row in self.colors)
        if stated != MASTER_COLOR_COUNT:
            raise ValueError(f"the console shows {MASTER_COLOR_COUNT} colors, got {stated}")

        return self

    @classmethod
    def load(cls) -> MasterPalette:
        """The palette the package ships."""
        return load_yaml_model(COLORS_PATH, cls)

    def to_array(self) -> NDArray[np.uint8]:
        """The red, green and blue of every color, indexed by the console's color number."""
        triplets = [
            [
                int(color.removeprefix(HEX_PREFIX)[channel * CHANNEL_DIGITS : (channel + 1) * CHANNEL_DIGITS], HEX_BASE)
                for channel in range(CHANNEL_COUNT)
            ]
            for row in self.colors
            for color in row
        ]
        return np.array(triplets, dtype=np.uint8)
