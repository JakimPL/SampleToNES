from typing import Dict, Type

from sampletones_core.constants.enums import SelectorName

from .base import Selector
from .greedy import GreedySelector
from .viterbi import CandidateState, ViterbiSelector

SELECTORS: Dict[SelectorName, Type[Selector]] = {
    SelectorName.GREEDY: GreedySelector,
    SelectorName.VITERBI: ViterbiSelector,
}

__all__ = [
    "Selector",
    "GreedySelector",
    "ViterbiSelector",
    "CandidateState",
    "SELECTORS",
]
