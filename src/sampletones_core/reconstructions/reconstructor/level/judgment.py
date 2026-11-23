from dataclasses import dataclass
from typing import Final, List, Self, Sequence, Tuple

import numpy as np

from sampletones_core.instructions import InstructionUnion, TriangleInstruction
from sampletones_core.reconstructions.reconstructor.stems.models.choice import StemChoice

BASS_DISTANCE: Final[int] = 1
LEAST_CONFIRMED_SHARE: Final[float] = 0.6


@dataclass(frozen=True)
class ChosenFrame:
    """A standing frame as the joint assignment chooses it at one working level, its stem on its own channels.

    The head of each column the stem holds is what the choice settles on the channel
    (``StemChoice``). A frame quieter at the level than a channel renders leaves its stem silent,
    holding no channel.

    Attributes:
        choices: The channels the stem holds in the frame, each with its column.
        note: The triangle note the frame's bass was read on.
    """

    choices: Tuple[StemChoice, ...]
    note: int

    @property
    def chosen(self) -> bool:
        """Whether the stem holds a channel in the frame."""
        return bool(self.choices)

    @property
    def cost(self) -> float:
        """The frame's cost as chosen: the cheapest head of the stem's columns.

        Raises:
            ValueError: If the stem holds no channel in the frame.
        """
        return min(choice.cost for choice in self.choices)

    @property
    def confirms(self) -> bool:
        """Whether a channel the stem holds plays the triangle within ``BASS_DISTANCE`` semitones of the note read.

        The note read centers a run, which spreads a note over its neighbors, so a triangle on a
        neighbor of it plays the bass too.
        """
        return any(self._plays_bass(choice.instruction) for choice in self.choices)

    def _plays_bass(self, instruction: InstructionUnion) -> bool:
        """Whether ``instruction`` sounds a triangle note within ``BASS_DISTANCE`` semitones of the note read."""
        return (
            isinstance(instruction, TriangleInstruction)
            and instruction.on
            and abs(instruction.pitch - self.note) <= BASS_DISTANCE
        )


@dataclass(frozen=True)
class Judgment:
    """How the joint assignment chooses a sample of a recording's standing frames at one working level.

    A level read holds where, moved there, the triangle plays the bass the frames were read on, and
    the frames as chosen cost less than at the first level (``holds_over``). A frame left silent at
    a level counts among the frames the triangle leaves the bass in, and outside the median cost.

    Attributes:
        cost: The median cost of the frames the stem holds a channel in, infinite where it holds
            none.
        confirmed: The share of the frames whose triangle plays the bass they were read on.
    """

    cost: float
    confirmed: float

    @classmethod
    def of(cls, frames: Sequence[ChosenFrame]) -> Self:
        """The judgment of ``frames``, a sample chosen at one level; an empty sample confirms nothing."""
        costs: List[float] = [frame.cost for frame in frames if frame.chosen]
        return cls(
            cost=float(np.median(costs)) if costs else float("inf"),
            confirmed=sum(frame.confirms for frame in frames) / len(frames) if frames else 0.0,
        )

    def holds_over(self, first: Self) -> bool:
        """Whether the level this judges holds against the first level, judged ``first``.

        It holds where the triangle plays the bass on at least ``LEAST_CONFIRMED_SHARE`` of the
        frames, and the frames cost less than at the first level.
        """
        return self.confirmed >= LEAST_CONFIRMED_SHARE and self.cost < first.cost
