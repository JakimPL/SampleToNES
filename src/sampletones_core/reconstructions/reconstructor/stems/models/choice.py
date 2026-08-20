from typing import NamedTuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.fft import Fragment
from sampletones_core.instructions import InstructionUnion


class StemChoice(NamedTuple):
    stem_id: int
    channel_name: ChannelName
    instruction: InstructionUnion
    approximation: Fragment
    cost: float
