from dataclasses import dataclass
from typing import Dict, Protocol

from sampletones_core.constants.enums import AssignmentMethod, ChannelName
from sampletones_core.fft import Fragment
from sampletones_core.generators import GeneratorUnion
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.assignment.frame import assign_frame
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.assigner import JointAssigner
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.models.frame_assignment import StemFrameAssignment


class FrameAssigner(Protocol):
    """Assigns one recording's frames, one at a time, each answered whole: every channel held or resting."""

    def assign(self, fragments: Dict[int, Fragment]) -> StemFrameAssignment:
        """Assigns one frame of every stem, keyed by stem id."""


@dataclass(frozen=True)
class PicksAssigner:
    """Assigns every frame one pick at a time, for as long as a pick helps, as ``assign_frame`` does."""

    stems_config: StemsConfig
    channels: Dict[ChannelName, GeneratorUnion]
    matcher: FrameMatcher
    lattice_width: int

    def assign(self, fragments: Dict[int, Fragment]) -> StemFrameAssignment:
        return assign_frame(fragments, self.stems_config, self.channels, self.matcher, self.lattice_width)


def frame_assigner(
    method: AssignmentMethod,
    stems_config: StemsConfig,
    channels: Dict[ChannelName, GeneratorUnion],
    matcher: FrameMatcher,
    lattice_width: int,
) -> FrameAssigner:
    """The assigner a recording's frames are assigned with under ``method``.

    Raises:
        ValueError: If the joint method is asked for stems that share a channel.
    """
    match method:
        case AssignmentMethod.PICKS:
            return PicksAssigner(stems_config, channels, matcher, lattice_width)
        case AssignmentMethod.JOINT:
            return JointAssigner(stems_config, channels, matcher, lattice_width)
