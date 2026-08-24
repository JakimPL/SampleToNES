from typing import FrozenSet, Optional

from pydantic import BaseModel

from sampletones_application.view_model.shared.footprint import SampleFootprintViewModel
from sampletones_core.constants.enums import ChannelName


class InstrumentViewModel(BaseModel, frozen=True):
    """What the instruments panel shows of an instrument: its name and the values it states.

    An instrument is its envelopes and the roots they are measured against, so the panel renders one
    instrument rather than a tab per channel.
    """

    name: str
    root_pitch: int
    root_period: int
    loop_point: Optional[int]

    @property
    def loops(self) -> bool:
        """Whether the instrument repeats its envelopes rather than playing them once."""
        return self.loop_point is not None


class ReconstructionInstrumentsViewModel(BaseModel, frozen=True):
    """What the instruments panel renders: the voice in front of it, and how it is read.

    A reconstruction holds a tab per channel whatever it sounds, so a channel standing by stays
    editable and giving it an envelope puts it in play. :attr:`playing_channels` is what the panel
    reads to mark the standing-by tabs and to offer their export. An instrument is one set every
    channel reads, so :attr:`instrument` is what the panel renders instead.
    """

    reconstruction_loaded: bool
    playing_channels: FrozenSet[ChannelName]
    footprint: Optional[SampleFootprintViewModel]
    instrument: Optional[InstrumentViewModel] = None

    @property
    def edits_an_instrument(self) -> bool:
        """Whether the panel is showing an instrument rather than a reconstruction's channels."""
        return self.instrument is not None

    @property
    def is_open(self) -> bool:
        """Whether the panel has a voice in front of it at all."""
        return self.reconstruction_loaded or self.edits_an_instrument
