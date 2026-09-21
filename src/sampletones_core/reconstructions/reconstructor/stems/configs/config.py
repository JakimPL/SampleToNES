from functools import cached_property
from typing import Dict, FrozenSet, List, Self

from pydantic import ConfigDict, Field, model_validator

from sampletones_core.constants.enums import ChannelName
from sampletones_core.data import DataModel
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings


class StemsConfig(DataModel):
    """The setup a run hands its channels out under: the stems, and the order they pick in.

    Each entry states what its recording is converted with, the count and the drives included, so
    the setup carries every per-recording choice and the hierarchy alone speaks for the run.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    entries: List[StemEntry] = Field(
        default_factory=list,
        description="The competing stems, each with what its recording is converted with",
    )
    hierarchy: StemsHierarchy = Field(
        default_factory=StemsHierarchy,
        description="The precedence structure of the stems assignment",
    )

    @classmethod
    def single_entry(cls, settings: StemSettings) -> Self:
        """The setup of one stem converted with ``settings`` on a single precedence level.

        One entry covering every channel it is given, sounding all of them at once, reproduces the
        classic greedy pick, so this setup describes both a single-file conversion and the stems
        pipeline's simplest case.
        """
        return cls(
            entries=[StemEntry(id=0, settings=settings)],
            hierarchy=StemsHierarchy(levels=[[0]]),
        )

    @cached_property
    def bent_channels(self) -> FrozenSet[ChannelName]:
        """Every channel some stem carries toward its own recording."""
        return frozenset(channel for entry in self.entries for channel in entry.settings.bends)

    @cached_property
    def entries_by_id(self) -> Dict[int, StemEntry]:
        """The entries keyed by the id the hierarchy names them with."""
        return {entry.id: entry for entry in self.entries}

    @cached_property
    def covered_channels(self) -> FrozenSet[ChannelName]:
        """Every channel some stem may occupy, which is the set an assignment puts in play."""
        return frozenset(channel for entry in self.entries for channel in entry.settings.channels)

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
