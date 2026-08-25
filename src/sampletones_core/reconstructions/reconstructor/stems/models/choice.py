from typing import NamedTuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.fft import Fragment
from sampletones_core.instructions import InstructionUnion
from sampletones_core.reconstructions.reconstructor.matching import Column


class StemChoice(NamedTuple):
    """One stem's claim on one channel for one frame.

    The instruction, approximation and cost are what won the channel and what the residual
    the next pick sees was formed from. The column holds the alternatives the decoder chooses
    among for the same channel and frame, the winner among them.
    """

    stem_id: int
    channel_name: ChannelName
    instruction: InstructionUnion
    approximation: Fragment
    cost: float
    column: Column
