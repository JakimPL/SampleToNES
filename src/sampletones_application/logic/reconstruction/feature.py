from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters import Features
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.selection import StemSelection


@dataclass(frozen=True)
class FeatureData:
    """The envelopes of every channel a reconstruction holds, keyed by channel.

    A reconstruction exports one entry per channel whatever it sounds, so a subscript answers
    for any of them and :attr:`Features.has_frames` says which ones play. The entries answer
    for the part the reader is listening to, which is what keeps the plot, the figures and an
    export stating one and the same thing.
    """

    channels: Dict[ChannelName, Features]

    def __getitem__(self, channel_name: ChannelName) -> Features:
        return self.channels[channel_name]

    @classmethod
    def heard(cls, reconstruction: Reconstruction, selection: StemSelection) -> FeatureData:
        """The envelopes of the part each channel plays for the recordings a reader hears.

        What is drawn, what is measured and what an export writes are one reading, so a
        recording switched off on a channel leaves the envelopes it held there, and a channel
        every recording is switched off on describes no frame at all.

        Args:
            reconstruction: The reconstruction being read.
            selection: The recordings the reader hears, channel by channel.

        Returns:
            FeatureData: One entry per channel the reconstruction exports.
        """
        return cls(
            channels={
                ChannelName(generator_name): features
                for generator_name, features in reconstruction.export_heard(selection).items()
            }
        )
