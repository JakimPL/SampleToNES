from dataclasses import dataclass
from typing import Final, List, Optional, Self, Sequence, Tuple

import numpy as np

from .reading import FrameReading

LEAST_STANDING_FRAMES: Final[int] = 4
LEAST_STANDING_SHARE: Final[float] = 0.5
MOST_SPREAD: Final[float] = 0.5
READING_WIDTH: Final[float] = 0.03
LOWER_QUARTILE: Final[float] = 25.0
UPPER_QUARTILE: Final[float] = 75.0


@dataclass(frozen=True)
class StandingFrame:
    """A frame read with a triangle line holding its bass.

    Attributes:
        stem_id: The stem whose recording the frame is of.
        index: The frame's place in that recording.
        reading: Where its bass stands.
    """

    stem_id: int
    index: int
    reading: FrameReading


@dataclass(frozen=True)
class LevelReading:
    """What a recording's frames read say about the level its triangle line stands at.

    A bass resting between its notes or changing note within a frame's window reads quieter than it
    plays, and a pulse sharing its note lifts a frame's reading, while the frames holding the line
    read alike. A line therefore stands where it holds the bass of enough of the frames read
    (``stands``) and their readings agree (``agrees``), and it stands at the reading the most others
    lie near (``densest``).

    Attributes:
        sampled: How many frames were read.
        standing: The frames read whose bass a triangle line holds, stem by stem, each stem's in
            frame order.
    """

    sampled: int
    standing: Tuple[StandingFrame, ...]

    @classmethod
    def pooled(cls, readings: Sequence[Self]) -> Self:
        """Several stems' readings read together, in the order given."""
        return cls(
            sampled=sum(reading.sampled for reading in readings),
            standing=tuple(frame for reading in readings for frame in reading.standing),
        )

    @property
    def level(self) -> Optional[float]:
        """The level the frames agree the bass stands at, ``None`` where no line stands or the readings disagree."""
        if not self.stands or not self.agrees:
            return None

        return self.densest

    @property
    def stands(self) -> bool:
        """Whether a triangle line holds the bass of at least ``LEAST_STANDING_SHARE`` of the frames read.

        A line holds ``LEAST_STANDING_FRAMES`` frames at least, however few were read.
        """
        count = len(self.standing)
        return count >= LEAST_STANDING_FRAMES and count >= LEAST_STANDING_SHARE * self.sampled

    @property
    def agrees(self) -> bool:
        """Whether the readings agree: their quartiles lie at most ``MOST_SPREAD`` of their median apart.

        The median must lie above zero.
        """
        levels = self.levels
        middle = float(np.median(levels))
        lower, upper = np.percentile(levels, [LOWER_QUARTILE, UPPER_QUARTILE])
        return middle > 0.0 and bool(upper - lower <= MOST_SPREAD * middle)

    @property
    def densest(self) -> float:
        """The reading the most others lie near, each weighed by a Gaussian ``READING_WIDTH`` wide in log level.

        A level is a factor, so nearness is read in its logarithm. Of readings lying alike near the
        others, the earliest standing frame's stands.
        """
        levels = self.levels
        logs = np.log(levels)
        distances = (logs[:, None] - logs[None, :]) / READING_WIDTH
        nearness = np.exp(-0.5 * distances**2).sum(axis=1)
        return float(levels[int(np.argmax(nearness))])

    @property
    def levels(self) -> np.ndarray:
        """Each standing frame's reading, in order."""
        return np.array([frame.reading.level for frame in self.standing])

    def sample(self, count: int) -> List[StandingFrame]:
        """At most ``count`` of the standing frames, spread evenly over them from the first to the last."""
        if len(self.standing) <= count:
            return list(self.standing)

        return [self.standing[int(position)] for position in np.linspace(0, len(self.standing) - 1, count)]
