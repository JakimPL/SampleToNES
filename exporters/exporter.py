from typing import Dict, Generic, List, Mapping, Union

import numpy as np

from frequencies import pitch_to_frequency
from timers.phase import PhaseTimer
from typehints.general import FeatureKey, FeatureValue
from typehints.instructions import InstructionType


class Exporter(Generic[InstructionType]):
    def __call__(
        self, instructions: List[InstructionType], as_string: bool = True
    ) -> Mapping[FeatureKey, Union[str, int, np.ndarray]]:
        features: Mapping[FeatureKey, FeatureValue] = self.get_features(instructions)
        if as_string:
            return {
                key: (" ".join(map(str, value)) if isinstance(value, np.ndarray) else str(value))
                for key, value in features.items()
            }

        return features

    def get_features(self, instructions: List[InstructionType]) -> Dict[FeatureKey, FeatureValue]:
        raise NotImplementedError("Subclasses must implement this method")

    def pitch_to_timer(self, pitch: int) -> int:
        frequency = pitch_to_frequency(pitch)
        return PhaseTimer.frequency_to_timer(frequency)
