from typing import Dict, List, Literal, Union

import numpy as np

from frequencies import pitch_to_frequency
from instructions.instruction import Instruction
from timers.phase import PhaseTimer

FeatureKey = Literal["initial_pitch", "volume", "arpeggio", "pitch", "hi_pitch", "duty_cycle"]
FeatureValue = Union[int, np.ndarray]


class Exporter:
    def __call__(
        self, instructions: List[Instruction], as_string: bool = True
    ) -> Dict[FeatureKey, Union[str, FeatureValue]]:
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
        frequency = pitch_to_frequency(pitch)
        return PhaseTimer.frequency_to_timer(frequency)
