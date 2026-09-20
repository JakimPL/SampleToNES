from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from sampletones_application.logic.reconstruction.ownership import (
    ownership_lane,
    record_positions,
    tells_recordings_apart,
)
from sampletones_application.view_model.shared.ownership import OwnershipLaneViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters import Features
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.selection import StemSelection


@dataclass(frozen=True)
class FeatureData:
    """The envelopes of every channel a reconstruction holds, and who holds each of their frames.

    A reconstruction exports one entry per channel whatever it sounds, so a subscript answers
    for any of them and :attr:`Features.has_frames` says which ones play. The entries answer
    for the part the reader is listening to, which is what keeps the plot, the figures and an
    export stating one and the same thing.

    The lanes are read from the same part, frame for frame, so a stretch painted under a
    dimension's bars stands under the frames that dimension draws. A document answering to one
    recording has nothing to tell apart and carries no lane.

    Attributes:
        channels: The envelopes each channel plays.
        ownership: The recordings behind each channel's frames, where several stand on the record.
    """

    channels: Dict[ChannelName, Features]
    ownership: Dict[ChannelName, OwnershipLaneViewModel]

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
        channels = {
            ChannelName(generator_name): features
            for generator_name, features in reconstruction.export_heard(selection).items()
        }
        return cls(channels=channels, ownership=cls._lanes(reconstruction, selection, channels))

    @staticmethod
    def _lanes(
        reconstruction: Reconstruction,
        selection: StemSelection,
        channels: Dict[ChannelName, Features],
    ) -> Dict[ChannelName, OwnershipLaneViewModel]:
        """The stretches under each channel's bars, held to the frames those bars describe."""
        stems_data = reconstruction.stems_data
        if not tells_recordings_apart(stems_data):
            return {}

        positions = record_positions(stems_data)
        owned = stems_data.assignments_by_channel
        return {
            channel_name: ownership_lane(
                channel_name,
                owned[channel_name][: features.frame_count],
                positions,
                selection.stems_for(channel_name),
            )
            for channel_name, features in channels.items()
            if features.has_frames and channel_name in owned
        }
