from dataclasses import dataclass, field
from typing import Any

import numpy as np

from sampletones_application.ui.elements.graphs.layers.layer import Layer
from sampletones_core.generators import MIXER_LEVELS
from sampletones_core.library import InstructionLibraryFragment
from sampletones_shared.types.application import Color

_DEFAULT_COLOR: Color = (255, 255, 255, 255)
_DEFAULT_LINE_THICKNESS: float = 1.5


@dataclass(frozen=True)
class InstructionLayer(Layer):
    data: InstructionLibraryFragment[Any]
    name: str
    color: Color = field(default_factory=lambda: _DEFAULT_COLOR)
    line_thickness: float = _DEFAULT_LINE_THICKNESS

    def __post_init__(self) -> None:
        mixer = MIXER_LEVELS[self.data.generator_class]
        data = self.data.data.astype(np.float32) / mixer
        object.__setattr__(self, "x_data", np.arange(len(data)).astype(np.float32))
        object.__setattr__(self, "y_data", data)
