from dataclasses import dataclass
from statistics import fmean
from typing import Dict, Final, Mapping, Tuple

from sampletones_tools.calibration.referee.protocol import SCORE_READING, Judgment

LOWEST_READING: Final[str] = "lowest"
HIGHEST_READING: Final[str] = "highest"


@dataclass(frozen=True)
class OracleReading:
    """The audio referees' judgments of one written sound's frames, rendered from several starting states.

    No transcription settles where the noise's sequence stands, so a sound's frames played exactly
    score as its state falls. The oracle reads each referee as the mean over the starts,
    which is what a conversion naming every frame right scores in expectation, and keeps the
    score's lowest and highest beside it, the range such a conversion lands in.

    Attributes:
        starts: Every referee's judgment of each start's render, by referee name, one mapping per start.
    """

    starts: Tuple[Mapping[str, Judgment], ...]

    def readings(self) -> Dict[str, Dict[str, float]]:
        """Each referee's readings: every reading's mean over the starts, then its score's lowest and highest.

        The referees and the readings keep the order the first start's judgments hold them in.
        """
        readings: Dict[str, Dict[str, float]] = {}
        for referee in self.starts[0]:
            judged = [start[referee].readings() for start in self.starts]
            means = {name: fmean(reading[name] for reading in judged) for name in judged[0]}
            scores = [reading[SCORE_READING] for reading in judged]
            readings[referee] = {**means, LOWEST_READING: min(scores), HIGHEST_READING: max(scores)}

        return readings

    def typical(self, referee: str) -> int:
        """The start whose score under ``referee`` lies nearest its mean, the earliest of equally near ones.

        It is the start a listener hears for the oracle, the render that scores as the oracle reads.
        """
        scores = [start[referee].score for start in self.starts]
        mean = fmean(scores)
        distances = [abs(score - mean) for score in scores]
        return distances.index(min(distances))
