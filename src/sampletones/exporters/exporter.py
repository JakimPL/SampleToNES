from typing import Generic, List, Optional

import numpy as np

from sampletones.instructions import InstructionT
from sampletones.timers import PhaseTimer
from sampletones.typehints.general import FeatureMap
from sampletones.utils import pitch_to_frequency, trim

from .feature import Features


class Exporter(Generic[InstructionT]):
    def __call__(
        self,
        instructions: List[InstructionT],
    ) -> Features:
        feature_map = self.get_feature_map(instructions)
        return self.to_features(feature_map)

    def to_features(self, feature_map: FeatureMap) -> Features:
        features = Features.from_feature_map(feature_map)
        last_nonzero_volume_index: Optional[int] = None
        try:
            last_nonzero_volume_index = features.volume.nonzero()[0][-1] + 2
        except IndexError:
            pass

        for key, value in features.items():
            if isinstance(value, np.ndarray):
                trimmed_value = trim(value[:last_nonzero_volume_index])
                features[key] = trimmed_value

        return features

    def get_feature_map(self, instructions: List[InstructionT]) -> FeatureMap:
        raise NotImplementedError("Subclasses must implement this method")

    @staticmethod
    def pitch_to_timer(pitch: int) -> int:
        frequency = pitch_to_frequency(pitch)
        return PhaseTimer.frequency_to_timer(frequency)
