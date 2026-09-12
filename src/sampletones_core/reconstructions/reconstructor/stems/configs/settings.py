from functools import cached_property
from typing import FrozenSet, List, Self

from pydantic import ConfigDict, Field, model_validator

from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName
from sampletones_core.data import DataModel


class StemSettings(DataModel):
    """What one recording is converted with: the channels it may occupy, and which of them it bends.

    A recording's settings are one value, so the list a reader sets a run up in, the entry that run
    records, and whoever reads the record later all state the same thing. A further per-recording
    choice is a field here, and each of those readers gains it in the same step.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    channels: List[ChannelName] = Field(
        ...,
        description="The channels the recording may occupy",
    )
    bends: List[ChannelName] = Field(
        ...,
        description="The channels whose notes the recording carries to the divider it sounds",
    )

    @cached_property
    def channel_set(self) -> FrozenSet[ChannelName]:
        """The channels the recording may occupy, in the form an assignment tests membership against."""
        return frozenset(self.channels)

    @cached_property
    def bend_set(self) -> FrozenSet[ChannelName]:
        """The channels the recording bends, in the form the refinement tests membership against."""
        return frozenset(self.bends)

    @model_validator(mode="after")
    def _bends_reach_their_channels(self) -> Self:
        """Holds a bend to a channel the recording occupies and whose hardware loads a divider.

        Raises:
            ValueError: If a bent channel lies outside the recording's own channels, or names the
                noise channel, whose sixteen periods stand at fixed distances from each other.
        """
        unheld = self.bend_set - self.channel_set
        if unheld:
            raise ValueError(f"Bent channels lie outside the ones occupied: {sorted(unheld)}")

        toneless = self.bend_set - TONE_CHANNELS
        if toneless:
            raise ValueError(f"Bent channels read no bend: {sorted(toneless)}")

        return self
