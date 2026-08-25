from typing import AbstractSet, Dict, FrozenSet, Iterable, Self

from pydantic import BaseModel, ConfigDict

from sampletones_core.constants.enums import ChannelName


class StemSelection(BaseModel):
    """Which stems a reader is listening to, channel by channel.

    A stem is heard on a channel once its id stands in that channel's set, so one recording
    carries a channel while another keeps quiet on it. What the recordings are mixed into is
    drawn from the stems heard anywhere, which is what :meth:`any_channel` answers.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    channels: Dict[ChannelName, FrozenSet[int]]

    @classmethod
    def everywhere(
        cls,
        stem_ids: AbstractSet[int],
        channels: Iterable[ChannelName],
    ) -> Self:
        """The selection hearing every stem of ``stem_ids`` on every channel of ``channels``."""
        return cls(channels={channel: frozenset(stem_ids) for channel in channels})

    def stems_for(self, channel: ChannelName) -> FrozenSet[int]:
        """The stems heard on one channel, empty where the channel names none."""
        return self.channels.get(channel, frozenset())

    def any_channel(self) -> FrozenSet[int]:
        """The stems heard on at least one channel."""
        return frozenset().union(*self.channels.values()) if self.channels else frozenset()
