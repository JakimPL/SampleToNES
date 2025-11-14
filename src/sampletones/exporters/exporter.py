from typing import Generic, List, Optional

import numpy as np

from sampletones.instructions import InstructionType
from sampletones.timers import PhaseTimer
from sampletones.typehints.general import FeatureMap
from sampletones.utils import pitch_to_frequency

from .feature import Features


class Exporter(Generic[InstructionType]):
    def __call__(
        self,
        instructions: List[InstructionType],
    ) -> Features:
        feature_map = self.get_feature_map(instructions)
        return self.to_features(feature_map)

    def to_features(self, feature_map: FeatureMap) -> Features:
        features = Features.from_feature_map(feature_map)
        last_nonzero_volume_index: Optional[int] = None
        try:
            last_nonzero_volume_index = features.volume.nonzero()[0][-1] + 1
        except IndexError:
            pass

        for key, value in features.items():
            if isinstance(value, np.ndarray):
                trimmed_value = np.trim_zeros(value[:last_nonzero_volume_index], "b")
                features[key] = trimmed_value

        return features

    def get_feature_map(self, instructions: List[InstructionType]) -> FeatureMap:
        raise NotImplementedError("Subclasses must implement this method")

    @staticmethod
    def pitch_to_timer(pitch: int) -> int:
        frequency = pitch_to_frequency(pitch)
        return PhaseTimer.frequency_to_timer(frequency)
