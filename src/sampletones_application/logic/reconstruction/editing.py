from dataclasses import dataclass
from typing import Dict, Optional, Protocol, Union

from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exporters import Features
from sampletones_core.types.feature import FeatureValue


@dataclass(frozen=True)
class ReconstructionEdit:
    """The channels of a loaded reconstruction, each with the envelopes it carries."""

    channels: Dict[ChannelName, Features]


@dataclass(frozen=True)
class ShapeEdit:
    """The one envelope set a shape carries, with the roots and the loop point it states.

    Attributes:
        voice_id: The shape an edit is written back into.
        name: The name the panel titles it by.
        features: The envelopes, read as the channel offering every dimension a shape writes.
        root_pitch: The note the tonal channels measure the arpeggio against.
        root_period: The period the noise channel measures the arpeggio against.
        loop_point: The tick the envelopes repeat from, or ``None`` where they play once.
    """

    voice_id: str
    name: str
    features: Features
    root_pitch: int
    root_period: int
    loop_point: Optional[int]


EditedInstrument = Union[ReconstructionEdit, ShapeEdit]


class InstrumentEditingProtocol(Protocol):
    """Where the instruments panel's envelopes come from, and where an edit to a shape goes.

    The panel edits one voice at a time — the channels of a loaded reconstruction, or a shape's
    own set — so it asks what is in front of it and renders whichever answer comes back. A
    reconstruction's envelopes travel back out through the regeneration service; a shape stands on
    no audio, so its edits are written here.
    """

    def edited_instrument(self) -> Optional[EditedInstrument]:
        """What the panel is editing, or ``None`` while it holds nothing."""

    def write_envelope(self, feature_key: FeatureKey, data: FeatureValue) -> None:
        """Writes one dimension of the shape in front of the panel."""

    def write_roots(self, *, pitch: int, period: int) -> None:
        """Moves the roots the shape in front of the panel is measured against."""

    def write_loop_point(self, loop_point: Optional[int]) -> None:
        """Sets the tick the shape in front of the panel repeats from."""
