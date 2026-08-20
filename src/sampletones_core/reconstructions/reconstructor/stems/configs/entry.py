from typing import List

from pydantic import ConfigDict, Field

from sampletones_core.constants.enums import ChannelName
from sampletones_core.data import DataModel


class StemEntry(DataModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: int = Field(
        ...,
        description="Identifier of the stem the hierarchy references",
    )
    channels: List[ChannelName] = Field(
        ...,
        description="The channels the stem may occupy",
    )
