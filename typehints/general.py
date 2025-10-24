from typing import Any, Callable, List, Literal, Optional, Tuple, Union

import numpy as np

Initials = Optional[Tuple[Any, ...]]

GeneratorName = Literal["pulse1", "pulse2", "triangle", "noise"]
GENERATOR_NAMES: List[GeneratorName] = ["pulse1", "pulse2", "triangle", "noise"]

InstructionClassNameValues = "PulseInstruction", "TriangleInstruction", "NoiseInstruction"
InstructionClassName = Literal["PulseInstruction", "TriangleInstruction", "NoiseInstruction"]
INSTRUCTION_CLASS_NAMES: List[InstructionClassName] = ["PulseInstruction", "TriangleInstruction", "NoiseInstruction"]

GeneratorClassNameValues = "PulseGenerator", "TriangleGenerator", "NoiseGenerator"
GeneratorClassName = Literal["PulseGenerator", "TriangleGenerator", "NoiseGenerator"]
GENERATOR_CLASS_NAMES: List[GeneratorClassName] = ["PulseGenerator", "TriangleGenerator", "NoiseGenerator"]

FeatureKey = Literal["initial_pitch", "volume", "arpeggio", "pitch", "hi_pitch", "duty_cycle"]
FeatureValue = Union[int, np.ndarray]

UnaryTransformation = Callable[[np.ndarray], np.ndarray]
BinaryTransformation = Callable[[np.ndarray, np.ndarray], np.ndarray]
MultaryTransformation = Callable[..., np.ndarray]
