from __future__ import annotations

from typing import Dict

from pydantic import BaseModel, ConfigDict

from sampletones_shared.utils.serialization import load_yaml_model
from sampletones_tools.player.graphics.paths import SHAPES_PATH
from sampletones_tools.player.graphics.sheet.drawing import Drawing


class Shapes(BaseModel):
    """Every drawing the screen uses beyond its text, by name.

    Attributes:
        shapes: Each drawing, by the name tile groups refer to it with.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    shapes: Dict[str, Drawing]

    @classmethod
    def load(cls) -> Shapes:
        """The shapes the package ships."""
        return load_yaml_model(SHAPES_PATH, cls)
