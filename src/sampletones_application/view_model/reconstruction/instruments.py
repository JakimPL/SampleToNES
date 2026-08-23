from typing import FrozenSet, Optional

from pydantic import BaseModel

from sampletones_application.view_model.shared.footprint import SampleFootprintViewModel
from sampletones_core.constants.enums import ChannelName


class ShapeInstrumentViewModel(BaseModel, frozen=True):
    """What the instruments panel shows of a shape: its name and the values it states.

    A shape is its envelopes and the roots they are measured against, so the panel renders one
    instrument rather than a tab per channel.
    """

    name: str
    root_pitch: int
    root_period: int
    loop_point: Optional[int]

    @property
    def loops(self) -> bool:
        """Whether the shape repeats its envelopes rather than playing them once."""
        return self.loop_point is not None


class ReconstructionInstrumentsViewModel(BaseModel, frozen=True):
    """What the instruments panel renders: the voice in front of it, and how it is read.

    A reconstruction holds a tab per channel whatever it sounds, so a channel standing by stays
    editable and giving it an envelope puts it in play. :attr:`playing_channels` is what the panel
    reads to mark the standing-by tabs and to offer their export. A shape holds one instrument
    every channel reads, so :attr:`shape` is what the panel renders instead.
    """

    reconstruction_loaded: bool
    playing_channels: FrozenSet[ChannelName]
    footprint: Optional[SampleFootprintViewModel]
    shape: Optional[ShapeInstrumentViewModel] = None

    @property
    def edits_a_shape(self) -> bool:
        """Whether the panel is showing a shape rather than a reconstruction's channels."""
        return self.shape is not None

    @property
    def is_open(self) -> bool:
        """Whether the panel has a voice in front of it at all."""
        return self.reconstruction_loaded or self.edits_a_shape
