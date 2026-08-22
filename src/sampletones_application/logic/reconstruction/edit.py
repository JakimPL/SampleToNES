from dataclasses import dataclass
from typing import Optional, TypeAlias, Union

from sampletones_application.logic.history.transaction import CoalesceKey
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.reconstructions import Reconstruction


@dataclass(frozen=True)
class InstrumentEdit:
    """A regenerated instrument paired with the channel and feature the reader moved.

    Carrying the request context alongside the fresh reconstruction lets the project history
    record which channel and feature an edit touched.
    """

    reconstruction: Reconstruction
    channel_name: ChannelName
    feature_key: FeatureKey

    def coalesce_key(self, sample_id: str) -> Optional[CoalesceKey]:
        """Consecutive edits of one sample run together, so a graph movement records one entry."""
        return (sample_id,)


@dataclass(frozen=True)
class StemRemoval:
    """A recording taken out of the reconstruction, named as the history reports it."""

    reconstruction: Reconstruction
    stem_name: str

    def coalesce_key(self, _sample_id: str) -> Optional[CoalesceKey]:
        """Each removal stands on its own, so one undo puts one recording back."""
        return None


ReconstructionEdit: TypeAlias = Union[InstrumentEdit, StemRemoval]
