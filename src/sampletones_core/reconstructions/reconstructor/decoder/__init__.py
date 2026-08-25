from typing import Dict, Type

from sampletones_core.constants.enums import SelectorName

from .base import ChannelLattice, Decoder, Lattices, Streams
from .greedy import GreedyDecoder
from .viterbi import ViterbiDecoder

DECODERS: Dict[SelectorName, Type[Decoder]] = {
    SelectorName.GREEDY: GreedyDecoder,
    SelectorName.VITERBI: ViterbiDecoder,
}

__all__ = [
    "DECODERS",
    "ChannelLattice",
    "Decoder",
    "GreedyDecoder",
    "Lattices",
    "Streams",
    "ViterbiDecoder",
]
