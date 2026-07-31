from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, cast

import numpy as np

from sampletones_core.constants.enums import FeatureKey, GeneratorName
from sampletones_core.exporters import Features
from sampletones_core.reconstructions import Reconstruction


@dataclass(frozen=True)
class FeatureData:
    generators: Dict[GeneratorName, Features]

    def __getitem__(self, generator_name: GeneratorName) -> Features:
        return self.generators[generator_name]

    @classmethod
    def load(cls, reconstruction: Reconstruction) -> FeatureData:
        exported_features = reconstruction.export()

        generators = {}
        for generator_name_str, features in exported_features.items():
            generator_name = GeneratorName(generator_name_str)
            feature = Features(
                initial_pitch=cast(int, features.get(FeatureKey.INITIAL_PITCH)),
                volume=cast(np.ndarray, features.get(FeatureKey.VOLUME)),
                arpeggio=cast(np.ndarray, features.get(FeatureKey.ARPEGGIO)),
                pitch=cast(Optional[np.ndarray], features.get(FeatureKey.PITCH)),
                hi_pitch=cast(Optional[np.ndarray], features.get(FeatureKey.HI_PITCH)),
                duty_cycle=cast(Optional[np.ndarray], features.get(FeatureKey.DUTY_CYCLE)),
            )

            generators[generator_name] = feature

        return cls(generators=generators)

    def get_generator_features(
        self,
        generator_name: GeneratorName,
    ) -> Optional[Features]:
        return self.generators.get(generator_name)
