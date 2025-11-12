from pathlib import Path
from typing import Dict, List, Optional, cast

import numpy as np
from pydantic import BaseModel, ConfigDict

from sampletones.constants import FeatureKey, GeneratorName
from sampletones.reconstructor import Reconstruction
from sampletones.typehints import FeatureValue
from sampletones.utils import write_fti


class Feature(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    generator_name: GeneratorName
    initial_pitch: int
    volume: np.ndarray
    arpeggio: np.ndarray
    pitch: Optional[np.ndarray]
    hi_pitch: Optional[np.ndarray]
    duty_cycle: Optional[np.ndarray]

    def _feature_map(self) -> Dict[FeatureKey, Optional[FeatureValue]]:
        return {
            FeatureKey.INITIAL_PITCH: self.initial_pitch,
            FeatureKey.VOLUME: self.volume,
            FeatureKey.ARPEGGIO: self.arpeggio,
            FeatureKey.PITCH: self.pitch,
            FeatureKey.HI_PITCH: self.hi_pitch,
            FeatureKey.DUTY_CYCLE: self.duty_cycle,
        }

    def __getitem__(self, feature_key: FeatureKey) -> FeatureValue:
        value = self._feature_map().get(feature_key)
        if value is None:
            raise KeyError(feature_key)
        return value

    def get(self, feature_key: FeatureKey) -> Optional[FeatureValue]:
        return self._feature_map().get(feature_key)

    def keys(self) -> List[FeatureKey]:
        return [key for key, value in self._feature_map().items() if value is not None]

    def save(self, filepath: Path, instrument_name: str) -> None:
        write_fti(
            filename=filepath,
            instrument_name=instrument_name,
            volume=cast(Optional[np.ndarray], self.volume),
            arpeggio=cast(Optional[np.ndarray], self.arpeggio),
            pitch=cast(Optional[np.ndarray], self.pitch),
            hi_pitch=cast(Optional[np.ndarray], self.hi_pitch),
            duty_cycle=cast(Optional[np.ndarray], self.duty_cycle),
        )


class FeatureData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    generators: Dict[GeneratorName, Feature]

    def __getitem__(self, generator_name: GeneratorName) -> Feature:
        return self.generators[generator_name]

    @classmethod
    def load(cls, reconstruction: Reconstruction) -> "FeatureData":
        exported_features = reconstruction.export(as_string=False)

        generators = {}
        for generator_name_str, features in exported_features.items():
            generator_name = GeneratorName(generator_name_str)
            feature = Feature(
                generator_name=generator_name,
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

    def get_generator_features(self, generator_name: GeneratorName) -> Optional[Feature]:
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
