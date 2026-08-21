from typing import List, Self

from pydantic import ConfigDict, Field, model_validator

from sampletones_core.constants.algorithm import (
    ALL_STEMS_CHANNEL_CAP,
    DEFAULT_STEMS_CHANNEL_CAP,
)
from sampletones_core.constants.enums import ChannelName
from sampletones_core.data import DataModel
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy


class StemsConfig(DataModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    entries: List[StemEntry] = Field(
        default_factory=list,
        description="The competing stems and the channels each may occupy",
    )
    hierarchy: StemsHierarchy = Field(
        default_factory=StemsHierarchy,
        description="The precedence structure of the stems assignment",
    )
    channel_cap: int = Field(
        default=DEFAULT_STEMS_CHANNEL_CAP,
        ge=1,
        description="The most channels one stem holds per frame",
    )

    @classmethod
    def single_entry(
        cls,
        channels: List[ChannelName],
        *,
        channel_cap: int = ALL_STEMS_CHANNEL_CAP,
    ) -> Self:
        """The setup for one stem covering ``channels``, the classic run's shape.

        One entry holding every channel on a single precedence level reproduces the classic
        greedy pick when the cap equals the channel count, so this setup describes both a
        single-file conversion and the stems pipeline's simplest case.
        """
        return cls(
            entries=[StemEntry(id=0, channels=channels)],
            hierarchy=StemsHierarchy(levels=[[0]]),
            channel_cap=channel_cap,
        )

    @model_validator(mode="after")
    def _validate_unique_entry_ids(self) -> Self:
        ids = [entry.id for entry in self.entries]
        if len(set(ids)) != len(ids):
            raise ValueError("Stem entries must have unique ids")

        return self
