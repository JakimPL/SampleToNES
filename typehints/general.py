from typing import Any, Literal, Optional, Tuple, Union

import numpy as np

Initials = Optional[Tuple[Any, ...]]

InstructionClassNameValues = "PulseInstruction", "TriangleInstruction", "NoiseInstruction"
InstructionClassName = Literal["PulseInstruction", "TriangleInstruction", "NoiseInstruction"]

GeneratorClassNameValues = "PulseGenerator", "TriangleGenerator", "NoiseGenerator"
GeneratorClassName = Literal["PulseGenerator", "TriangleGenerator", "NoiseGenerator"]

FeatureKey = Literal["initial_pitch", "volume", "arpeggio", "pitch", "hi_pitch", "duty_cycle"]
FeatureValue = Union[int, np.ndarray]
