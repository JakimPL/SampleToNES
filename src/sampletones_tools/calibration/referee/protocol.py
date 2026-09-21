from dataclasses import dataclass
from typing import Dict, Final, Mapping, Protocol

import numpy as np

SCORE_READING: Final[str] = "score"


@dataclass(frozen=True)
class Judgment:
    """A referee's reading of one estimate: the score it ranks by and the parts that score breaks into.

    Attributes:
        score: The distance a report ranks by; zero for identical signals.
        components: Named readings behind the score, keyed by the constants the referee declares.
    """

    score: float
    components: Mapping[str, float]

    def readings(self) -> Dict[str, float]:
        """Every reading of the judgment by name, the score first under ``SCORE_READING``."""
        return {SCORE_READING: self.score, **self.components}


class Referee(Protocol):
    """Full-reference audio distance: zero for identical signals, growing with audible difference."""

    @property
    def name(self) -> str: ...

    def judge(self, reference: np.ndarray, estimate: np.ndarray) -> Judgment: ...
