from typing import FrozenSet

from pydantic import BaseModel

from sampletones_core.constants.enums import GeneratorName


class SequencerChannelsViewModel(BaseModel, frozen=True):
    """Which tracker channels are silenced, for the panels that show the mute cue.

    Muting belongs to the listening session: the project holds every channel, so saving,
    export, and the history stack all read the full song.
    """

    muted: FrozenSet[GeneratorName]

    def is_muted(self, generator: GeneratorName) -> bool:
        return generator in self.muted

    @property
    def all_muted(self) -> bool:
        """Whether every channel is silenced, the state the master column's click restores from."""
        return self.muted == frozenset(GeneratorName.items())
