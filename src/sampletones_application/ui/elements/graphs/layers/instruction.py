from dataclasses import dataclass
from typing import Any

import numpy as np

from sampletones_application.constants.graphs import COL_WAVEFORM_DEFAULT, VAL_WAVEFORM_SAMPLE_THICKNESS
from sampletones_application.ui.elements.graphs.layers.layer import Layer
from sampletones_core.generators import MIXER_LEVELS
from sampletones_core.library import InstructionLibraryFragment
from sampletones_shared.types.application import Color


@dataclass(frozen=True)
class InstructionLayer(Layer):
    data: InstructionLibraryFragment[Any]
    name: str
    color: Color = COL_WAVEFORM_DEFAULT
    line_thickness: float = VAL_WAVEFORM_SAMPLE_THICKNESS

    def __post_init__(self) -> None:
        mixer = MIXER_LEVELS[self.data.generator_class]
        data = self.data.data.astype(np.float32) / mixer
        object.__setattr__(self, "x_data", np.arange(len(data)).astype(np.float32))
        object.__setattr__(self, "y_data", data)
