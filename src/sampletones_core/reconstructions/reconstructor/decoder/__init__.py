from typing import Dict, Type

from sampletones_core.constants.enums import SelectorName

from .base import Alternatives, ChannelLattice, Decoder, Lattices, PooledCombination, Pools, StemPools, Streams
from .combinations import CombinationsDecoder
from .greedy import GreedyDecoder
from .viterbi import ViterbiDecoder

DECODERS: Dict[SelectorName, Type[Decoder]] = {
    SelectorName.GREEDY: GreedyDecoder,
    SelectorName.VITERBI: ViterbiDecoder,
    SelectorName.COMBINATIONS: CombinationsDecoder,
}

__all__ = [
    "DECODERS",
    "Alternatives",
    "ChannelLattice",
    "CombinationsDecoder",
    "Decoder",
    "GreedyDecoder",
    "Lattices",
    "PooledCombination",
    "Pools",
    "StemPools",
    "Streams",
    "ViterbiDecoder",
]
