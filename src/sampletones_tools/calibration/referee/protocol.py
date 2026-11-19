from dataclasses import dataclass
from typing import Dict, Final, Mapping, Optional, Protocol

import numpy as np

from sampletones_core.reconstructions import Reconstruction
from sampletones_tools.calibration.corpus.truth import Truth

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


class ConversionReferee(Protocol):
    """Reads a conversion on its own, from what it recorded: zero for one that holds its decisions steady.

    A referee answers ``None`` for a conversion that holds nothing it reads.
    """

    @property
    def name(self) -> str: ...

    def judge(self, reconstruction: Reconstruction) -> Optional[Judgment]: ...


class TruthReferee(Protocol):
    """Reads a conversion against what its reference sound plays: zero for one that plays it exactly.

    A referee answers ``None`` for a sound whose truth holds nothing it reads, so a report averages
    only the sounds it judged.
    """

    @property
    def name(self) -> str: ...

    def judge(self, truth: Truth, reconstruction: Reconstruction) -> Optional[Judgment]: ...
