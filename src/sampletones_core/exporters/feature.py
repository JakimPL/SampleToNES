from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

import numpy as np
from pydantic import BaseModel, ConfigDict

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.famitracker.fti import write_fti
from sampletones_core.famitracker.model.instrument import Instrument2A03
from sampletones_core.famitracker.sequences.features import features_to_instrument_sequences
from sampletones_core.famitracker.sequences.truncation import SequenceTruncation
from sampletones_core.types.feature import FeatureMap, FeatureValue


class Features(BaseModel):
    """
    The per-dimension envelopes describing one FamiTracker instrument.

    Each field is the frame-by-frame envelope for one dimension — volume, arpeggio,
    pitch, hi-pitch, and duty cycle — alongside the ``initial_pitch`` the pitch envelope
    is relative to. An optional dimension is absent when the channel does not use it.
    The mapping interface (subscript, ``get``, ``keys``/``items``/``values``, ``in``)
    exposes the envelopes keyed by :class:`FeatureKey`, passing over absent ones.

    Attributes:
        initial_pitch: Reference pitch the pitch envelope is measured against.
        volume: Volume envelope.
        arpeggio: Arpeggio (relative pitch) envelope.
        pitch: Pitch envelope, or ``None`` when unused.
        hi_pitch: Fine-pitch envelope, or ``None`` when unused.
        duty_cycle: Duty-cycle envelope, or ``None`` when unused.
    """

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
    ) -> Features:
        """Builds features from a raw feature map.

        Args:
            feature_map: The per-dimension arrays keyed by :class:`FeatureKey`.

        Returns:
            Features: The features carrying those envelopes.
        """
        return cls(
            initial_pitch=cast(int, feature_map[FeatureKey.INITIAL_PITCH]),
            volume=cast(np.ndarray, feature_map[FeatureKey.VOLUME]),
            arpeggio=cast(np.ndarray, feature_map[FeatureKey.ARPEGGIO]),
            pitch=cast(Optional[np.ndarray], feature_map.get(FeatureKey.PITCH)),
            hi_pitch=cast(Optional[np.ndarray], feature_map.get(FeatureKey.HI_PITCH)),
            duty_cycle=cast(Optional[np.ndarray], feature_map.get(FeatureKey.DUTY_CYCLE)),
        )

    @property
    def feature_map(self) -> Dict[FeatureKey, Optional[FeatureValue]]:
        return {
            FeatureKey.INITIAL_PITCH: self.initial_pitch,
            FeatureKey.VOLUME: self.volume,
            FeatureKey.ARPEGGIO: self.arpeggio,
            FeatureKey.PITCH: self.pitch,
            FeatureKey.HI_PITCH: self.hi_pitch,
            FeatureKey.DUTY_CYCLE: self.duty_cycle,
        }

    def __getitem__(self, feature_key: FeatureKey) -> FeatureValue:
        value = self.feature_map.get(feature_key)
        if value is None:
            raise KeyError(feature_key)
        return value

    def __setitem__(self, feature_key: FeatureKey, value: FeatureValue) -> None:
        if feature_key == FeatureKey.INITIAL_PITCH:
            if not isinstance(value, int):
                raise TypeError(f"Expected int for {feature_key}, got {type(value)}")
        else:
            if not isinstance(value, np.ndarray):
                raise TypeError(f"Expected np.ndarray for {feature_key}, got {type(value)}")

        setattr(self, feature_key.name.lower(), value)

    def __contains__(self, feature_key: FeatureKey) -> bool:
        return feature_key in self.feature_map and self.feature_map[feature_key] is not None

    def get(self, feature_key: FeatureKey, default: Optional[Any] = None) -> Optional[FeatureValue]:
        return self.feature_map.get(feature_key, default)

    def keys(self) -> List[FeatureKey]:
        return [key for key, value in self.feature_map.items() if value is not None]

    def items(self) -> List[Tuple[FeatureKey, FeatureValue]]:
        return [(key, value) for key, value in self.feature_map.items() if value is not None]

    def values(self) -> List[FeatureValue]:
        return [value for value in self.feature_map.values() if value is not None]

    @property
    def frame_count(self) -> int:
        """The frame count the envelopes describe, taken from the longest populated dimension."""
        arrays = (self.volume, self.arpeggio, self.pitch, self.hi_pitch, self.duty_cycle)
        return max((len(array) for array in arrays if array is not None), default=0)

    def save(self, filepath: Path, instrument_name: str) -> Optional[SequenceTruncation]:
        """Writes the features to a FamiTracker instrument (``.fti``) file.

        Builds a single 2A03 instrument from the envelopes and serializes it. Envelopes
        longer than a FamiTracker sequence holds reach the file as their opening frames,
        which the return value reports.

        Args:
            filepath: Destination path for the ``.fti`` file.
            instrument_name: Name stored in the instrument.

        Returns:
            Optional[SequenceTruncation]: The frames the sequence limit left out, and
                ``None`` when the file carries every frame.

        Raises:
            IOError: If the file cannot be written.
        """
        sequences = features_to_instrument_sequences(
            volume=self.volume,
            arpeggio=self.arpeggio,
            pitch=self.pitch,
            hi_pitch=self.hi_pitch,
            duty_cycle=self.duty_cycle,
            loop=False,
        )
        instrument = Instrument2A03(index=0, name=instrument_name, sequences=sequences)
        try:
            write_fti(filepath, instrument)
        except (
            FileNotFoundError,
            IOError,
            OSError,
            PermissionError,
            IsADirectoryError,
        ) as exception:
            raise IOError(f"Failed to save features to '{filepath}': {exception}") from exception

        return SequenceTruncation.measure(self.frame_count)
