from dataclasses import dataclass
from typing import Optional, Protocol, Union

from sampletones_application.view_model.reconstruction.envelopes import (
    ChannelEnvelopesViewModel,
)
from sampletones_core.constants.enums import FeatureKey
from sampletones_core.exporters import Features
from sampletones_core.features.envelope import Envelope
from sampletones_core.project.voices.instrument import Instrument


@dataclass(frozen=True)
class InstrumentEdit:
    """The one envelope set an instrument carries, as the panel has it in front of a reader.

    The pitch an instrument's arpeggio is measured from travels inside :attr:`features`, where
    an export reads it; a row states the note the voice sounds at, so nothing here edits it.

    Attributes:
        voice_id: The instrument an edit is written back into.
        name: The name the panel titles it by.
        features: The envelopes, read as the channel offering every dimension an instrument writes.
    """

    voice_id: str
    name: str
    features: Features


@dataclass(frozen=True)
class EnvelopesOwed:
    """A reconstruction in front of the panel whose envelopes the worker is still rendering.

    An opening, an edit, a retune, an undo and a new choice of what is heard send the envelopes to
    the worker with the sound, so the document has channels to edit once they land, and an edit
    reaching the panel meanwhile goes nowhere.

    Attributes:
        opening: Whether no envelopes have landed for the document since it was opened, so the
            panel has none of it to keep showing.
    """

    opening: bool


EditedVoice = Union[ChannelEnvelopesViewModel, InstrumentEdit, EnvelopesOwed]


class InstrumentEditingProtocol(Protocol):
    """Where the instruments panel's envelopes come from, and where an edit to an instrument goes.

    The panel edits one voice at a time — the channels of a loaded reconstruction, or an instrument's
    own set — so it asks what is in front of it and renders whichever answer comes back. A
    reconstruction's envelopes travel back out through the regeneration service; an instrument stands on
    no audio, so its edits are written here.
    """

    def edited_instrument(self) -> Optional[EditedVoice]:
        """What the panel is editing: an instrument, a reconstruction's channels, or a reconstruction whose
        channels are on their way from the worker; ``None`` while it holds nothing.
        """

    def write_envelope(self, feature_key: FeatureKey, envelope: Envelope[int]) -> None:
        """Writes one dimension of the instrument in front of the panel."""


class InstrumentAuditionProtocol(Protocol):
    """Where the voice an audition sounds comes from.

    An audition plays the instrument the tab is showing, at the note a key names, so it reads the
    voice whole rather than the envelopes a panel draws: the frames it sounds are made from the
    envelopes and the pitch they are measured against together.
    """

    @property
    def instrument(self) -> Optional[Instrument]:
        """The instrument in front of the tab, or ``None`` while it shows a recording or nothing."""
