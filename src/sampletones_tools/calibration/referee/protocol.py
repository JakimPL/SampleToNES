from dataclasses import dataclass
from typing import Dict, Final, Mapping, Optional, Protocol

import numpy as np

from sampletones_core.reconstructions import Reconstruction
from sampletones_tools.calibration.corpus.truth import Truth
from sampletones_tools.calibration.trace import SearchTrace

SCORE_READING: Final[str] = "score"


@dataclass(frozen=True)
class Judgment:
    """A referee's reading of one conversion: the score it ranks by and the readings that score breaks into.

    A lower score is closer, and zero is a conversion the referee finds no fault with. Each referee
    states the unit and the direction of its score and of every reading it declares.

    Attributes:
        score: The distance a report ranks by; zero where the referee finds no fault.
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


class TraceReferee(Protocol):
    """Reads a conversion's search against what its reference sound plays: zero for a search that found it.

    A referee answers ``None`` for a sound whose truth holds nothing it reads.
    """

    @property
    def name(self) -> str: ...

    def judge(self, truth: Truth, trace: SearchTrace, reconstruction: Reconstruction) -> Optional[Judgment]: ...
