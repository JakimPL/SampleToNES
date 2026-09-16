from __future__ import annotations

from functools import cached_property
from typing import Dict, List

from pydantic import ConfigDict, Field

from sampletones_core.constants.enums import ChannelName
from sampletones_core.data import DataModel
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings


class StemsData(DataModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    config: StemsConfig = Field(
        ...,
        description="The stems setup the assignment was made under",
    )
    assignments: List[ChannelAssignment] = Field(
        ...,
        description="Per channel, the stem holding each frame",
    )

    @classmethod
    def single_entry(
        cls,
        settings: StemSettings,
        assignments: List[ChannelAssignment],
    ) -> StemsData:
        """The record of one stem converted with ``settings``, holding the frames ``assignments`` name."""
        return cls(
            config=StemsConfig.single_entry(settings),
            assignments=assignments,
        )

    @cached_property
    def assignments_by_channel(self) -> Dict[ChannelName, List[int]]:
        """The per-frame stem ids each channel carries, keyed by channel."""
        return {item.channel_name: item.stem_ids for item in self.assignments}
