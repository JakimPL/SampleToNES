from typing import FrozenSet

from pydantic import BaseModel

from sampletones_core.constants.enums import ChannelName


class ReconstructorPanelViewModel(BaseModel, frozen=True):
    channels: FrozenSet[ChannelName]
    drive: float
