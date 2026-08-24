from dataclasses import dataclass
from typing import Dict, Optional, Protocol, Union

from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exporters import Features
from sampletones_core.features.envelope import Envelope


@dataclass(frozen=True)
class ReconstructionEdit:
    """The channels of a loaded reconstruction, each with the envelopes it carries."""

    channels: Dict[ChannelName, Features]


@dataclass(frozen=True)
class InstrumentEdit:
    """The one envelope set an instrument carries, with the pitch its arpeggio is measured from.

    Attributes:
        voice_id: The instrument an edit is written back into.
        name: The name the panel titles it by.
        features: The envelopes, read as the channel offering every dimension an instrument writes.
        initial_pitch: The note the tonal channels measure the arpeggio against.
        initial_period: The period the noise channel measures the arpeggio against.
    """

    voice_id: str
    name: str
    features: Features
    initial_pitch: int
    initial_period: int


EditedVoice = Union[ReconstructionEdit, InstrumentEdit]


class InstrumentEditingProtocol(Protocol):
    """Where the instruments panel's envelopes come from, and where an edit to an instrument goes.

    The panel edits one voice at a time — the channels of a loaded reconstruction, or an instrument's
    own set — so it asks what is in front of it and renders whichever answer comes back. A
    reconstruction's envelopes travel back out through the regeneration service; an instrument stands on
    no audio, so its edits are written here.
    """

    def edited_instrument(self) -> Optional[EditedVoice]:
        """What the panel is editing, or ``None`` while it holds nothing."""

    def write_envelope(self, feature_key: FeatureKey, envelope: Envelope[int]) -> None:
        """Writes one dimension of the instrument in front of the panel."""

    def write_roots(self, *, pitch: int, period: int) -> None:
        """Moves the roots the instrument in front of the panel is measured against."""
