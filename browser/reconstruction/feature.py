from typing import Dict, List, Optional

import numpy as np
from pydantic import BaseModel

from constants.enums import FeatureKey, GeneratorName
from reconstructor.reconstruction import Reconstruction


class FeatureData(BaseModel):
    generators: Dict[GeneratorName, Dict[FeatureKey, np.ndarray]]

    @classmethod
    def load(cls, reconstruction: Reconstruction) -> "FeatureData":
        exported_features = reconstruction.export(as_string=False)

        generators = {}
        for generator_name_str, features in exported_features.items():
            generator_name = GeneratorName(generator_name_str)
            numpy_features = {key: value for key, value in features.items() if isinstance(value, np.ndarray)}
            generators[generator_name] = numpy_features

        return cls(generators=generators)

    def get_generator_names(self) -> List[GeneratorName]:
        return list(self.generators.keys())

    def has_generator(self, generator_name: GeneratorName) -> bool:
        return generator_name in self.generators

    def get_generator_features(self, generator_name: GeneratorName) -> Optional[Dict[FeatureKey, np.ndarray]]:
        return self.generators.get(generator_name)

    def get_feature_for_generator(self, generator_name: GeneratorName, feature_key: FeatureKey) -> Optional[np.ndarray]:
        features = self.get_generator_features(generator_name)
        return features.get(feature_key) if features else None

    def has_feature_for_generator(self, generator_name: GeneratorName, feature_key: FeatureKey) -> bool:
        features = self.get_generator_features(generator_name)
        return feature_key in features if features else False

    def get_first_generator_with_feature(self, feature_key: FeatureKey) -> Optional[GeneratorName]:
        for generator_name, features in self.generators.items():
            if feature_key in features:
                return generator_name
        return None

    class Config:
        arbitrary_types_allowed = True
