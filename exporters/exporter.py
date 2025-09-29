from typing import Dict, List, Literal, Union

import numpy as np

from generators.generator import Generator
from instructions.instruction import Instruction
from timer import Timer

FeatureKey = Literal["initial_pitch", "volume", "arpeggio", "pitch", "hi_pitch", "duty_cycle"]
FeatureValue = Union[int, np.ndarray]


class Exporter:
    def __init__(self, generator: Generator):
        self.generator = generator

    def __call__(self, instructions: List[Instruction], as_string: bool = True) -> Dict[FeatureKey, str]:
        features = self.get_features(instructions)
        if as_string:
            return {
                key: (" ".join(map(str, value)) if isinstance(value, np.ndarray) else str(value))
                for key, value in features.items()
            }

        return features

    def get_features(self, instructions: List[Instruction]) -> Dict[FeatureKey, FeatureValue]:
        raise NotImplementedError("Subclasses must implement this method")

    def pitch_to_timer(self, pitch: int) -> int:
        frequency = self.generator.frequency_table[pitch]
        return Timer.frequency_to_timer(frequency)
