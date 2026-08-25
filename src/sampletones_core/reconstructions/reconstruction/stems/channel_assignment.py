from typing import List

from pydantic import ConfigDict, Field

from sampletones_core.constants.enums import ChannelName
from sampletones_core.data import DataModel


class ChannelAssignment(DataModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    channel_name: ChannelName = Field(
        ...,
        description="The channel whose frames are assigned",
    )
    stem_ids: List[int] = Field(
        ...,
        description="The stem holding the channel in each frame",
    )
