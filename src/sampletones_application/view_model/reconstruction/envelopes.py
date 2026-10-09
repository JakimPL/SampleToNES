from typing import Dict

from pydantic import BaseModel

from sampletones_application.view_model.shared.ownership import OwnershipLaneViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters import Features


class ChannelEnvelopesViewModel(BaseModel, extra="forbid", frozen=True):
    """What the instruments panel plots: each channel's envelopes and who holds their frames.

    The two are read from one part of the document, frame for frame, so a stretch painted under
    a dimension's bars stands under the frames those bars draw. A voice written by hand answers
    to no recording, and so does a document holding one, so both carry envelopes alone.

    Attributes:
        channels: The envelopes each channel plots.
        ownership: The recordings behind each channel's frames.
    """

    channels: Dict[ChannelName, Features]
    ownership: Dict[ChannelName, OwnershipLaneViewModel]

    def __getitem__(self, channel_name: ChannelName) -> Features:
        return self.channels[channel_name]

    def lane(self, channel_name: ChannelName) -> OwnershipLaneViewModel:
        """The stretches under one channel's bars, empty where no recording is told apart there."""
        return self.ownership.get(channel_name, OwnershipLaneViewModel(channel_name=channel_name, runs=()))
