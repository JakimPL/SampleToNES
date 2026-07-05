from typing import Dict, Type

from sampletones_core.constants.enums import SelectorName

from .base import ScoredCandidate, Selector
from .greedy import GreedySelector
from .viterbi import ViterbiSelector

SELECTORS: Dict[SelectorName, Type[Selector]] = {
    SelectorName.GREEDY: GreedySelector,
    SelectorName.VITERBI: ViterbiSelector,
}

__all__ = [
    "Selector",
    "GreedySelector",
    "ViterbiSelector",
    "ScoredCandidate",
    "SELECTORS",
]
