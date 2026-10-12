from enum import StrEnum
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


class InstrumentsShowing(StrEnum):
    """What the instruments panel shows of the voice in front of it.

    A reconstruction's envelopes are the worker's to export. A document just opened has none yet,
    so the panel says they are being prepared. An edit, a retune, an undo and a new choice of what
    is heard owe the next ones, so the panel keeps the ones it drew and takes no edit until they
    land.
    """

    NOTHING = "nothing"
    PREPARING = "preparing"
    KEPT = "kept"
    EDITABLE = "editable"


class ReconstructionInstrumentsViewModel(BaseModel, frozen=True, extra="forbid"):
    """What the instruments panel renders: the voice in front of it, and how it is read.

    A reconstruction holds a tab per channel whatever it sounds, so a channel standing by stays
    editable and giving it an envelope puts it in play. :attr:`playing_channels` is what the panel
    reads to mark the standing-by tabs and to offer their export. An instrument is one set every
    channel reads, so :attr:`instrument` is what the panel renders instead. While the envelopes
    are :attr:`InstrumentsShowing.KEPT`, the panel keeps the tabs, the figures and the bars it drew
    and reads nothing else of the view.
    """

    showing: InstrumentsShowing
    playing_channels: FrozenSet[ChannelName]
    footprint: Optional[VoiceFootprintViewModel]
    instrument: Optional[InstrumentViewModel] = None

    @property
    def edits_an_instrument(self) -> bool:
        """Whether the panel is showing an instrument rather than a reconstruction's channels."""
        return self.instrument is not None

    @property
    def reconstruction_loaded(self) -> bool:
        """Whether a reconstruction stands in front of the panel, its envelopes landed or on their way."""
        return self.instrument is None and self.showing is not InstrumentsShowing.NOTHING

    @property
    def is_open(self) -> bool:
        """Whether the panel draws envelopes: an instrument's, or a reconstruction's landed or kept."""
        return self.showing in (InstrumentsShowing.KEPT, InstrumentsShowing.EDITABLE)

    @property
    def is_locked(self) -> bool:
        """Whether the panel keeps what it drew and takes no edit until the worker lands the next envelopes."""
        return self.showing is InstrumentsShowing.KEPT
