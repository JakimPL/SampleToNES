from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from sampletones_core.constants.enums import ChannelName
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
        """The envelopes each of a reconstruction's channels plays, keyed by channel.

        Args:
            reconstruction: The reconstruction being read.

        Returns:
            FeatureData: One entry per channel the reconstruction exports.
        """
        return cls(
            channels={
                ChannelName(generator_name): features for generator_name, features in reconstruction.export().items()
            }
        )
