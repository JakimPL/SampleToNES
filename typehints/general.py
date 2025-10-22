from typing import Any, Callable, Literal, Optional, Tuple, Union

import numpy as np

Initials = Optional[Tuple[Any, ...]]

InstructionClassNameValues = "PulseInstruction", "TriangleInstruction", "NoiseInstruction"
InstructionClassName = Literal["PulseInstruction", "TriangleInstruction", "NoiseInstruction"]

GeneratorClassNameValues = "PulseGenerator", "TriangleGenerator", "NoiseGenerator"
GeneratorClassName = Literal["PulseGenerator", "TriangleGenerator", "NoiseGenerator"]

FeatureKey = Literal["initial_pitch", "volume", "arpeggio", "pitch", "hi_pitch", "duty_cycle"]
FeatureValue = Union[int, np.ndarray]

UnaryTransformation = Callable[[np.ndarray], np.ndarray]
BinaryTransformation = Callable[[np.ndarray, np.ndarray], np.ndarray]
TransformationName = Literal["exp", "id"]
