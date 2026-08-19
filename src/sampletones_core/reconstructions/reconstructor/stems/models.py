from dataclasses import dataclass
from enum import StrEnum
from typing import Dict, FrozenSet, NamedTuple, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.fft import Fragment
from sampletones_core.instructions import InstructionUnion


class HierarchyMode(StrEnum):
    ROUND_ROBIN = "round_robin"
    STRICT = "strict"


@dataclass(frozen=True)
class Stem:
    """
    One audio source competing for channels in a reconstruction, identified by its
    id and restricted to the channels it may occupy.
    """

    id: int
    channels: FrozenSet[ChannelName]


@dataclass(frozen=True)
class StemHierarchy:
    """
    The precedence structure of a stems assignment: stems grouped into levels that
    pick in order, with a mode choosing how picks alternate between levels.
    """

    levels: Tuple[Tuple[int, ...], ...]
    mode: HierarchyMode


class StemChoice(NamedTuple):
    stem_id: int
    channel_name: ChannelName
    instruction: InstructionUnion
    approximation: Fragment
    cost: float


class StemFrameAssignment(NamedTuple):
    choices: Tuple[StemChoice, ...]

    @property
    def by_channel(self) -> Dict[ChannelName, StemChoice]:
        return {choice.channel_name: choice for choice in self.choices}
