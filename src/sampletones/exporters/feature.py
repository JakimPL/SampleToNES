from pathlib import Path
from typing import Dict, List, Optional, Tuple, cast

import numpy as np
from pydantic import BaseModel, ConfigDict

from sampletones.constants.enums import FeatureKey
from sampletones.typehints import FeatureMap, FeatureValue
from sampletones.utils import write_fti


class Features(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    initial_pitch: int
    volume: np.ndarray
    arpeggio: np.ndarray
    pitch: Optional[np.ndarray]
    hi_pitch: Optional[np.ndarray]
    duty_cycle: Optional[np.ndarray]

    @classmethod
    def from_feature_map(
        cls,
        feature_map: FeatureMap,
    ) -> "Features":
        return cls(
            initial_pitch=cast(int, feature_map[FeatureKey.INITIAL_PITCH]),
            volume=cast(np.ndarray, feature_map[FeatureKey.VOLUME]),
            arpeggio=cast(np.ndarray, feature_map[FeatureKey.ARPEGGIO]),
            pitch=cast(Optional[np.ndarray], feature_map.get(FeatureKey.PITCH)),
            hi_pitch=cast(Optional[np.ndarray], feature_map.get(FeatureKey.HI_PITCH)),
            duty_cycle=cast(Optional[np.ndarray], feature_map.get(FeatureKey.DUTY_CYCLE)),
        )

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

    def __setitem__(self, feature_key: FeatureKey, value: FeatureValue) -> None:
        setattr(self, feature_key.name.lower(), value)

    def __contains__(self, feature_key: FeatureKey) -> bool:
        return feature_key in self._feature_map() and self._feature_map()[feature_key] is not None

    def get(self, feature_key: FeatureKey) -> Optional[FeatureValue]:
        return self._feature_map().get(feature_key)

    def keys(self) -> List[FeatureKey]:
        return [key for key, value in self._feature_map().items() if value is not None]

    def items(self) -> List[Tuple[FeatureKey, FeatureValue]]:
        return [(key, value) for key, value in self._feature_map().items() if value is not None]

    def values(self) -> List[FeatureValue]:
        return [value for value in self._feature_map().values() if value is not None]

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
