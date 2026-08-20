from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, cast

import numpy as np

from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exporters import Features
from sampletones_core.reconstructions import Reconstruction


@dataclass(frozen=True)
class FeatureData:
    """The envelopes of every channel a reconstruction holds, keyed by channel.

    A reconstruction exports one entry per channel whatever it sounds, so a subscript answers
    for any of them and :attr:`Features.has_frames` says which ones play.
    """

    channels: Dict[ChannelName, Features]

    def __getitem__(self, channel_name: ChannelName) -> Features:
        return self.channels[channel_name]

    @classmethod
    def load(cls, reconstruction: Reconstruction) -> FeatureData:
        exported_features = reconstruction.export()

        channels = {}
        for generator_name_str, features in exported_features.items():
            channel_name = ChannelName(generator_name_str)
            feature = Features(
                initial_pitch=cast(int, features.get(FeatureKey.INITIAL_PITCH)),
                volume=cast(np.ndarray, features.get(FeatureKey.VOLUME)),
                arpeggio=cast(np.ndarray, features.get(FeatureKey.ARPEGGIO)),
                pitch=cast(Optional[np.ndarray], features.get(FeatureKey.PITCH)),
                hi_pitch=cast(Optional[np.ndarray], features.get(FeatureKey.HI_PITCH)),
                duty_cycle=cast(Optional[np.ndarray], features.get(FeatureKey.DUTY_CYCLE)),
            )

            channels[channel_name] = feature

        return cls(channels=channels)
