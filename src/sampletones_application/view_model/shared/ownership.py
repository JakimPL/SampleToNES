from typing import Tuple

from pydantic import BaseModel

from sampletones_core.constants.enums import ChannelName


class OwnershipRunViewModel(BaseModel, extra="forbid", frozen=True):
    """One stretch of a channel held by a single recording, as the ribbon paints it.

    Attributes:
        start_frame: The first frame of the stretch.
        end_frame: The frame the stretch runs up to, one past its last.
        stem_id: The stem holding it, which names the color.
        position: Where that stem's entry stands on the record, which picks the color.
        heard: Whether the reader hears that recording here, which settles how solidly it paints.
    """

    start_frame: int
    end_frame: int
    stem_id: int
    position: int
    heard: bool


class OwnershipLaneViewModel(BaseModel, extra="forbid", frozen=True):
    """One channel's stretch of ribbon: the channel it stands for and the runs along it."""

    channel_name: ChannelName
    runs: Tuple[OwnershipRunViewModel, ...]


class OwnershipRibbonViewModel(BaseModel, extra="forbid", frozen=True):
    """The recordings behind each stretch of what a reader is listening to.

    The ribbon reads along the same span the waveform above it draws, so a lane is stated in
    frames and the frame length turns them into the samples the plot counts. A document whose
    frames all answer to one recording has nothing to tell apart, so it offers no lanes.
    """

    lanes: Tuple[OwnershipLaneViewModel, ...]
    frame_length: int
    total_frames: int

    @classmethod
    def empty(cls) -> "OwnershipRibbonViewModel":
        """The ribbon standing for nothing, which is what a closed document leaves."""
        return cls(lanes=(), frame_length=1, total_frames=0)

    @property
    def is_drawn(self) -> bool:
        """Whether the ribbon has stretches to tell apart."""
        return bool(self.lanes) and self.total_frames > 0

    @property
    def total_samples(self) -> int:
        """The span the ribbon covers, in the samples the waveform's axis counts."""
        return self.total_frames * self.frame_length
