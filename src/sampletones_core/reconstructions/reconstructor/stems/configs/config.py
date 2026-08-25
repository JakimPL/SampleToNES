from functools import cached_property
from typing import Dict, FrozenSet, List, Self

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

    @cached_property
    def entries_by_id(self) -> Dict[int, StemEntry]:
        """The entries keyed by the id the hierarchy names them with."""
        return {entry.id: entry for entry in self.entries}

    @cached_property
    def covered_channels(self) -> FrozenSet[ChannelName]:
        """Every channel some stem may occupy, which is the set an assignment puts in play."""
        return frozenset(channel for entry in self.entries for channel in entry.channels)

    @property
    def frame_budget(self) -> int:
        """The most channels that can sound in one frame under this setup.

        Each stem holds at most ``channel_cap`` channels per frame and every held channel is one
        of the covered ones, so the smaller of the two bounds is what a frame can reach. The
        working level is measured against this budget, which keeps a capped run's target within
        what its channels render.
        """
        return min(len(self.covered_channels), len(self.entries) * self.channel_cap)

    @model_validator(mode="after")
    def _validate_unique_entry_ids(self) -> Self:
        ids = [entry.id for entry in self.entries]
        if len(set(ids)) != len(ids):
            raise ValueError("Stem entries must have unique ids")

        return self

    @model_validator(mode="after")
    def _validate_hierarchy_names_every_entry(self) -> Self:
        referenced = sorted(stem_id for level in self.hierarchy.levels for stem_id in level)
        if referenced != sorted(entry.id for entry in self.entries):
            raise ValueError("Hierarchy levels must name every stem exactly once")

        return self
