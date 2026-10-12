from typing import FrozenSet, Optional

from pydantic import BaseModel

from sampletones_application.view_model.shared.footprint import VoiceFootprintViewModel
from sampletones_core.constants.enums import ChannelName


class InstrumentViewModel(BaseModel, frozen=True):
    """What the instruments panel shows of an instrument, which is the name it is titled by.

    An instrument is one set of envelopes every channel reads, so the panel renders one instrument
    rather than a tab per channel, and each dimension states the item it repeats from itself.
    """

    name: str


class ReconstructionInstrumentsViewModel(BaseModel, frozen=True):
    """What the instruments panel renders: the voice in front of it, and how it is read.

    A reconstruction holds a tab per channel whatever it sounds, so a channel standing by stays
    editable and giving it an envelope puts it in play. :attr:`playing_channels` is what the panel
    reads to mark the standing-by tabs and to offer their export. An instrument is one set every
    channel reads, so :attr:`instrument` is what the panel renders instead. A reconstruction's
    envelopes are the worker's to export, so :attr:`envelopes_owed` says the document is open and
    its channels are on their way, which the panel states in place of its tabs.
    """

    reconstruction_loaded: bool
    envelopes_owed: bool
    playing_channels: FrozenSet[ChannelName]
    footprint: Optional[VoiceFootprintViewModel]
    instrument: Optional[InstrumentViewModel] = None

    @property
    def edits_an_instrument(self) -> bool:
        """Whether the panel is showing an instrument rather than a reconstruction's channels."""
        return self.instrument is not None

    @property
    def is_open(self) -> bool:
        """Whether the panel has a voice to draw: an instrument, or a reconstruction whose envelopes have landed."""
        return self.edits_an_instrument or (self.reconstruction_loaded and not self.envelopes_owed)
