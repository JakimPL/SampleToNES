from dataclasses import dataclass
from typing import Optional, TypeAlias, Union

from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.history.transaction import CoalesceKey
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.reconstructions import Reconstruction


@dataclass(frozen=True)
class ChannelEdit:
    """A regenerated instrument paired with the channel and feature the reader moved.

    Carrying the request context alongside the fresh reconstruction lets the project history
    record which channel and feature an edit touched.
    """

    reconstruction: Reconstruction
    channel_name: ChannelName
    feature_key: FeatureKey

    @property
    def history_action(self) -> HistoryAction:
        return HistoryAction.EDIT_RECONSTRUCTION

    def coalesce_key(self, voice_id: str) -> Optional[CoalesceKey]:
        """Consecutive edits of one sample run together, so a graph movement records one entry."""
        return (voice_id,)


@dataclass(frozen=True)
class StemRemoval:
    """A recording taken out of the reconstruction, named as the history reports it."""

    reconstruction: Reconstruction
    stem_name: str

    @property
    def history_action(self) -> HistoryAction:
        return HistoryAction.EDIT_RECONSTRUCTION

    def coalesce_key(self, _voice_id: str) -> Optional[CoalesceKey]:
        """Each removal stands on its own, so one undo puts one recording back."""
        return None


@dataclass(frozen=True)
class Retune:
    """The reconstruction re-timed to another NES frequency, every instruction carried over."""

    reconstruction: Reconstruction
    nes_frequency: int

    @property
    def history_action(self) -> HistoryAction:
        return HistoryAction.SET_NES_FREQUENCY

    def coalesce_key(self, _voice_id: str) -> Optional[CoalesceKey]:
        """A retune joins the rate change it follows, so one undo restores the rate and the audio together."""
        return (self.nes_frequency,)


ReconstructionEdit: TypeAlias = Union[ChannelEdit, StemRemoval, Retune]
