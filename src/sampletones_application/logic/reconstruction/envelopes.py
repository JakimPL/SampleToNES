from typing import Dict

from sampletones_application.logic.reconstruction.ownership import ownership_lanes
from sampletones_application.view_model.reconstruction.envelopes import (
    ChannelEnvelopesViewModel,
)
from sampletones_application.view_model.shared.ownership import OwnershipLaneViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters import Features
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.selection import StemSelection


def heard_envelopes(
    reconstruction: Reconstruction,
    selection: StemSelection,
) -> ChannelEnvelopesViewModel:
    """The envelopes of the part each channel plays for the recordings a reader hears.

    A reconstruction exports one entry per channel whatever it sounds, so a subscript answers
    for any of them and :attr:`Features.has_frames` says which ones play. What is drawn, what is
    measured and what an export writes are one reading, so a recording switched off on a channel
    leaves the envelopes it held there, and a channel every recording is switched off on
    describes no frame at all.

    Args:
        reconstruction: The reconstruction being read.
        selection: The recordings the reader hears, channel by channel.

    Returns:
        ChannelEnvelopesViewModel: One entry per channel the reconstruction exports.
    """
    channels = {
        ChannelName(generator_name): features
        for generator_name, features in reconstruction.export_heard(selection).items()
    }
    return ChannelEnvelopesViewModel(
        channels=channels,
        ownership=_lanes(reconstruction, selection, channels),
    )


def _lanes(
    reconstruction: Reconstruction,
    selection: StemSelection,
    channels: Dict[ChannelName, Features],
) -> Dict[ChannelName, OwnershipLaneViewModel]:
    """The stretches under each channel's bars, held to the frames those bars describe.

    Every channel the panel plots takes a lane, whatever the reader has switched on beneath the
    waveform: the channel boxes answer for the waveform, the stems card's muted tint and an
    export's scope. A lane reaches the last frame the channel's readings describe, so it stands
    over the bars drawn from them and no further.
    """
    stems_data = reconstruction.stems_data
    owned = stems_data.assignments_by_channel
    assignments = {
        channel_name: owned[channel_name][: features.frame_count]
        for channel_name, features in channels.items()
        if features.has_frames and channel_name in owned
    }
    return ownership_lanes(stems_data, assignments, selection.stems_for)
