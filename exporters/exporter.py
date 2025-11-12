from typing import Dict, Generic, List, Mapping, Union

import numpy as np

from constants.enums import FeatureKey
from timers.phase import PhaseTimer
from typehints.feature import FeatureValue
from typehints.instructions import InstructionType
from utils.frequencies import pitch_to_frequency


class Exporter(Generic[InstructionType]):
    def __call__(
        self, instructions: List[InstructionType], as_string: bool = False
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

    @staticmethod
    def pitch_to_timer(pitch: int) -> int:
        frequency = pitch_to_frequency(pitch)
        return PhaseTimer.frequency_to_timer(frequency)
