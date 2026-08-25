from functools import cached_property
from typing import FrozenSet, List, Self

from pydantic import ConfigDict, Field, model_validator

from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName
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
    bends: List[ChannelName] = Field(
        ...,
        description="The channels whose notes this stem carries to the divider its recording sounds",
    )

    @cached_property
    def channel_set(self) -> FrozenSet[ChannelName]:
        """The channels this stem may occupy, in the form an assignment tests membership against."""
        return frozenset(self.channels)

    @cached_property
    def bend_set(self) -> FrozenSet[ChannelName]:
        """The channels this stem bends, in the form the refinement tests membership against."""
        return frozenset(self.bends)

    @model_validator(mode="after")
    def _bends_reach_their_channels(self) -> Self:
        """Holds a bend to a channel the stem occupies and whose hardware loads a divider.

        Raises:
            ValueError: If a bent channel lies outside the stem's own channels, or names the
                noise channel, whose sixteen periods stand at fixed distances from each other.
        """
        unheld = self.bend_set - self.channel_set
        if unheld:
            raise ValueError(f"stem {self.id} bends channels it does not occupy: {sorted(unheld)}")

        toneless = self.bend_set - TONE_CHANNELS
        if toneless:
            raise ValueError(f"stem {self.id} bends channels that read no bend: {sorted(toneless)}")

        return self
