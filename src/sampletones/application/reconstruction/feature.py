from typing import Dict, List, Optional, cast

import numpy as np
from pydantic import BaseModel, ConfigDict

from sampletones.constants.enums import FeatureKey, GeneratorName
from sampletones.exporters import Features
from sampletones.reconstruction import Reconstruction
from sampletones.typehints import FeatureValue


class FeatureData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    generators: Dict[GeneratorName, Features]

    def __getitem__(self, generator_name: GeneratorName) -> Features:
        return self.generators[generator_name]

    @classmethod
    def load(cls, reconstruction: Reconstruction) -> "FeatureData":
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

    def get_generator_names(self) -> List[GeneratorName]:
        return list(self.generators.keys())

    def has_generator(self, generator_name: GeneratorName) -> bool:
        return generator_name in self.generators

    def get_generator_features(self, generator_name: GeneratorName) -> Optional[Features]:
        return self.generators.get(generator_name)

    def get_feature_for_generator(
        self, generator_name: GeneratorName, feature_key: FeatureKey
    ) -> Optional[FeatureValue]:
        features = self.get_generator_features(generator_name)
        return features.get(feature_key) if features else None

    def has_feature_for_generator(self, generator_name: GeneratorName, feature_key: FeatureKey) -> bool:
        features = self.get_generator_features(generator_name)
        return features.get(feature_key) is not None if features else False

    def get_first_generator_with_feature(self, feature_key: FeatureKey) -> Optional[GeneratorName]:
        for generator_name, features in self.generators.items():
            if features.get(feature_key) is not None:
                return generator_name
        return None
