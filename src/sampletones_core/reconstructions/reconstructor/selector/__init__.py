from typing import Dict, Type

from sampletones_core.constants.enums import SelectorName

from .base import Selector
from .greedy import GreedySelector
from .matching import ScoredCandidate
from .viterbi import ViterbiSelector

SELECTORS: Dict[SelectorName, Type[Selector]] = {
    SelectorName.GREEDY: GreedySelector,
    SelectorName.VITERBI: ViterbiSelector,
}

__all__ = [
    "SELECTORS",
    "GreedySelector",
    "ScoredCandidate",
    "Selector",
    "ViterbiSelector",
]
