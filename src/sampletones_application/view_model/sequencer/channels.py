from typing import FrozenSet

from pydantic import BaseModel

from sampletones_core.constants.enums import ChannelName


class SequencerChannelsViewModel(BaseModel, frozen=True):
    """Which tracker channels are silenced, for the panels that show the mute cue.

    Muting belongs to the listening session: the project holds every channel, so saving,
    export, and the history stack all read the full song.
    """

    muted: FrozenSet[ChannelName]

    def is_muted(self, channel: ChannelName) -> bool:
        return channel in self.muted

    def is_soloed(self, channel: ChannelName) -> bool:
        """Whether ``channel`` is the one channel left sounding.

        Solo is read back from the mute set the same way it is applied, so the menu names the
        gesture by what the mix currently sounds like.
        """
        return self.muted == frozenset(ChannelName.items()) - {channel}

    @property
    def any_muted(self) -> bool:
        """Whether at least one channel is silenced, the state a restore acts on."""
        return bool(self.muted)

    @property
    def all_muted(self) -> bool:
        """Whether every channel is silenced, the state the master column's click restores from."""
        return self.muted == frozenset(ChannelName.items())
