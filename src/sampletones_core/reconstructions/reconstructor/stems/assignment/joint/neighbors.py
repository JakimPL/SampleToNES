from dataclasses import dataclass
from typing import Dict, Self

from sampletones_core.configs.generation import ChannelInertia
from sampletones_core.constants.enums import ChannelName
from sampletones_core.fft import Fragment
from sampletones_core.reconstructions.reconstructor.decoder.base import Streams
from sampletones_core.reconstructions.reconstructor.decoder.transition import TransitionWeights
from sampletones_core.reconstructions.reconstructor.stems.models.frame_assignment import StemFrameAssignment
from sampletones_core.reconstructions.reconstructor.window.profiles import FrameProfiles
from sampletones_core.reconstructions.reconstructor.window.surroundings import (
    ChannelLine,
    ChannelSurroundings,
    surroundings,
)

from .assigner import JointAssigner
from .continuity import ChannelContinuity


@dataclass
class NeighborPass:
    """One pass assigning every frame of a decoded recording again, in turn, among what the frames around it play.

    A frame's analysis window reads its neighbors, so what they play is a fixed part of its reading.
    The frames before a frame play what this pass settled them on and the frames after it what the
    decode played, so each frame is decided among the latest choices around it, and its choice is
    settled into the lines before the next frame is decided. Each channel's choice also pays its
    inertia for breaking with the frames beside it.

    Attributes:
        assigner: The joint assignment the frames are decided by.
        lines: Every channel's frames, starting from the decode and settled as the pass goes.
        profiles: How each bin's window weighs the frames around the one it reads.
        weights: The decoder's charges for each kind of change, which inertia multiplies.
        inertia: Each channel's inertia.
    """

    assigner: JointAssigner
    lines: Dict[ChannelName, ChannelLine]
    profiles: FrameProfiles
    weights: TransitionWeights
    inertia: ChannelInertia

    @classmethod
    def over(
        cls,
        assigner: JointAssigner,
        streams: Streams,
        profiles: FrameProfiles,
        weights: TransitionWeights,
        inertia: ChannelInertia,
    ) -> Self:
        """A pass over the recording ``streams`` decoded."""
        return cls(
            assigner=assigner, lines=assigner.lines(streams), profiles=profiles, weights=weights, inertia=inertia
        )

    def assign(self, frame: int, fragments: Dict[int, Fragment]) -> StemFrameAssignment:
        """Assigns ``frame`` among what its neighbors play and settles the lines on its choice.

        Args:
            frame: The frame decided, the next one after those already settled.
            fragments: This frame of every stem, keyed by stem id.

        Returns:
            The frame's assignment.
        """
        assignment = self.assigner.assign_beside(fragments, self._heard(frame), self._continuity(frame))
        self.assigner.settle(self.lines, frame, assignment)
        return assignment

    def _heard(self, frame: int) -> Dict[ChannelName, ChannelSurroundings]:
        """What every channel's other frames leave in the frame's reading."""
        return {channel_name: surroundings(line, frame, self.profiles) for channel_name, line in self.lines.items()}

    def _continuity(self, frame: int) -> Dict[ChannelName, ChannelContinuity]:
        """What every channel plays beside the frame, and what its choice pays to break with it."""
        return {
            channel_name: ChannelContinuity.of(line, frame, self.weights, self.inertia.of(channel_name))
            for channel_name, line in self.lines.items()
        }
