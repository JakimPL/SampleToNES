from typing import NamedTuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion
from sampletones_core.reconstructions.reconstructor.contribution import Contribution
from sampletones_core.reconstructions.reconstructor.matching import Column, ScoredCandidate


class StemChoice(NamedTuple):
    """One stem's hold on one channel for one frame.

    The column holds the channel's alternatives scored in the stem's frame with the stem's other
    choices sounding, best first. Its head is what the assignment settled on: an instruction that
    sounds where the channel lowers the frame's cost, and the channel's silence where it does not.
    """

    stem_id: int
    channel_name: ChannelName
    column: Column

    @property
    def head(self) -> ScoredCandidate:
        return self.column[0]

    @property
    def instruction(self) -> InstructionUnion:
        return self.head.instruction

    @property
    def contribution(self) -> Contribution:
        return self.head.contribution

    @property
    def cost(self) -> float:
        return self.head.cost

    @property
    def sounding(self) -> bool:
        """Whether the channel sounds in the frame, which is what a mix adds up."""
        return self.head.instruction.on
