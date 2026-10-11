from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from pydantic import BaseModel

from sampletones_core.constants.enums import ChannelName


class OwnershipRunViewModel(BaseModel, extra="forbid", frozen=True):
    """One stretch of a channel held by a single recording, as the ribbon paints it.

    Attributes:
        start_frame: The first frame of the stretch.
        end_frame: The frame the stretch runs up to, one past its last.
        stem_id: The stem holding it, which picks the color.
        heard: Whether the reader hears that recording here, which settles how solidly it paints.
    """

    start_frame: int
    end_frame: int
    stem_id: int
    heard: bool


class OwnerStretchesViewModel(BaseModel, extra="forbid", frozen=True):
    """One recording's stretches along a lane, as a surface paints them in one piece.

    Attributes:
        stem_id: The stem holding the stretches, which picks the color.
        stretches: The first frame and the frame one past the last of each stretch, in frame order.
        heard: Whether the reader hears the recording on this lane, which settles how solidly it paints.
    """

    stem_id: int
    stretches: Tuple[Tuple[int, int], ...]
    heard: bool


def runs_by_owner(runs: Sequence[OwnershipRunViewModel]) -> Dict[int, OwnerStretchesViewModel]:
    """The runs of a lane gathered by the recording holding them, in the order the recordings first appear.

    A surface paints a recording's stretches as one piece however many times the lane divides, so
    what it draws costs as many pieces as the lane has owners. Hearing is chosen per channel, so a
    lane hears a recording on every stretch it holds or on none, and the recording's stretches share
    one reading of it.

    Args:
        runs: The lane's runs, in frame order.

    Returns:
        Dict[int, OwnerStretchesViewModel]: Each owner's stretches, keyed by stem id.
    """
    stretches: Dict[int, List[Tuple[int, int]]] = {}
    heard: Dict[int, bool] = {}
    for run in runs:
        stretches.setdefault(run.stem_id, []).append((run.start_frame, run.end_frame))
        heard[run.stem_id] = run.heard

    return {
        stem_id: OwnerStretchesViewModel(stem_id=stem_id, stretches=tuple(owned), heard=heard[stem_id])
        for stem_id, owned in stretches.items()
    }


class OwnershipLaneViewModel(BaseModel, extra="forbid", frozen=True):
    """One channel's stretch of ribbon: the channel it stands for and the runs along it.

    Hearing is chosen per channel, so the lane hears a recording on every stretch it holds or on none.
    """

    channel_name: ChannelName
    runs: Tuple[OwnershipRunViewModel, ...]

    def up_to(self, frame_count: int) -> Tuple[OwnershipRunViewModel, ...]:
        """The lane's runs over the first ``frame_count`` frames, the last of them ending there.

        A surface draws a reading as far as that reading goes, and the channel holds one lane for
        every reading taken from it, so a surface drawing fewer frames than the channel holds
        asks the lane for the stretches standing under them.
        """
        return tuple(
            run if run.end_frame <= frame_count else run.model_copy(update={"end_frame": frame_count})
            for run in self.runs
            if run.start_frame < frame_count
        )


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
    def empty(cls) -> OwnershipRibbonViewModel:
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
