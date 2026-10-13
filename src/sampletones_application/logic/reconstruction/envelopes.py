from dataclasses import dataclass
from typing import Dict, Mapping

from sampletones_application.logic.reconstruction.ownership import (
    ownership_lanes,
    tells_owners_apart,
)
from sampletones_application.view_model.reconstruction.envelopes import (
    ChannelEnvelopesViewModel,
)
from sampletones_application.view_model.shared.ownership import OwnershipLaneViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters import Features
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.ownership import runs_up_to
from sampletones_core.reconstructions.reconstruction.stems.selection import StemSelection


@dataclass(frozen=True)
class HeardEnvelopes:
    """The envelopes a document exports for one choice of recordings, beside that choice.

    The worker exports them with the sound it renders, so a landing installs envelopes made for
    the selection it names and tells a stale reading from a fresh one by that selection.

    Attributes:
        selection: The recordings the reader heard when the envelopes were exported.
        channels: The envelopes each channel exports for them.
    """

    selection: StemSelection
    channels: Mapping[ChannelName, Features]


def envelopes_view(
    reconstruction: Reconstruction,
    heard: HeardEnvelopes,
) -> ChannelEnvelopesViewModel:
    """The envelopes the instruments panel draws, built from what the document exported for the reader.

    Args:
        reconstruction: The reconstruction the envelopes were exported from.
        heard: The envelopes each channel exports for the recordings heard, beside that choice.

    Returns:
        ChannelEnvelopesViewModel: One entry per channel the reconstruction exports, with the
        stretches under each channel's bars.
    """
    channels = {ChannelName(generator_name): features for generator_name, features in heard.channels.items()}
    return ChannelEnvelopesViewModel(
        channels=channels,
        ownership=_lanes(reconstruction, heard.selection, channels),
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
    over the bars drawn from them and no further. A dimension's bars are one reading of one
    channel, so a document answering to a single owner has nothing beneath them to tell apart.
    """
    stems_data = reconstruction.stems_data
    if not tells_owners_apart(stems_data):
        return {}

    owned = stems_data.owner_runs_by_channel
    runs = {
        channel_name: runs_up_to(owned[channel_name], features.frame_count)
        for channel_name, features in channels.items()
        if features.has_frames and channel_name in owned
    }
    return ownership_lanes(runs, selection.stems_for)
