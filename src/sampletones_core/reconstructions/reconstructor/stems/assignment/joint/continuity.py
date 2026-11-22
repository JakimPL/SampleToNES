import itertools
from dataclasses import dataclass, replace
from typing import List, Mapping, Optional, Self, Sequence, Tuple

from sampletones_core.constants.enums import GeneratorClassName
from sampletones_core.instructions import InstructionUnion
from sampletones_core.reconstructions.reconstructor.decoder.transition import (
    TransitionWeights,
    transition_cost,
)
from sampletones_core.reconstructions.reconstructor.matching import Column, ScoredCandidate
from sampletones_core.reconstructions.reconstructor.window.surroundings import (
    ChannelLine,
)

from .catalog import KindCatalog
from .combinations import Rows
from .layout import StemLayout


@dataclass(frozen=True)
class ChannelContinuity:
    """What a channel plays in the frames on either side of a frame, and what the frame pays to break with it.

    The analysis window averages a channel over several frames, so a channel switched on and off
    from frame to frame reads as a level between the two, which the ear hears as flicker. A frame's
    choice pays the decoder's charges for changing from the frame before and to the frame after,
    ``inertia`` times over.

    Attributes:
        before: What the channel plays the frame before, ``None`` at the first frame.
        after: What the channel plays the frame after, ``None`` at the last frame.
        weights: The decoder's charges for each kind of change.
        inertia: How many times those charges a frame's choice pays.
    """

    before: Optional[InstructionUnion]
    after: Optional[InstructionUnion]
    weights: TransitionWeights
    inertia: float

    @classmethod
    def of(cls, line: ChannelLine, frame: int, weights: TransitionWeights, inertia: float) -> Self:
        """The continuity of ``line`` around ``frame``."""
        return cls(
            before=line.instructions[frame - 1] if frame > 0 else None,
            after=line.instructions[frame + 1] if frame + 1 < len(line.instructions) else None,
            weights=weights,
            inertia=inertia,
        )

    def charge(self, instruction: InstructionUnion) -> float:
        """What the frame pays for playing ``instruction`` beside the frames around it."""
        changes = 0.0
        if self.before is not None:
            changes += transition_cost(self.before, instruction, self.weights)

        if self.after is not None:
            changes += transition_cost(instruction, self.after, self.weights)

        return self.inertia * changes


@dataclass(frozen=True)
class StemContinuity:
    """What a stem's channels play beside a frame, and what each combination pays to break with it.

    Pulses the stem drives alike sound the same on either channel, so a combination pays for the
    order of its pulses that breaks least.

    Attributes:
        channels: Each channel's continuity, in the layout's channel order, ``None`` where the frame's
            choice pays nothing.
    """

    channels: Tuple[Optional[ChannelContinuity], ...]

    @classmethod
    def free(cls, layout: StemLayout) -> Self:
        """A stem whose frame chooses freely of the frames beside it."""
        return cls(channels=(None,) * len(layout.slots))

    @property
    def binding(self) -> bool:
        """Whether a combination pays anything for breaking with the frames beside the frame."""
        return any(channel is not None and channel.inertia > 0 for channel in self.channels)

    def charge(self, layout: StemLayout, catalogs: Mapping[GeneratorClassName, KindCatalog], rows: Rows) -> float:
        """What the frame pays for sounding ``rows`` beside the frames around it."""
        if not self.binding:
            return 0.0

        pulses = layout.interchangeable_pulses
        every_place = range(len(layout.slots))
        return min(
            self._paid(layout, catalogs, _reordered(rows, pulses, order), every_place)
            for order in itertools.permutations(pulses)
        )

    def beside(self, layout: StemLayout, catalogs: Mapping[GeneratorClassName, KindCatalog]) -> List[Rows]:
        """The combinations the frame before and the frame after play, which a frame may hold through."""
        if not self.binding:
            return []

        held: List[Rows] = []
        for played in (self._played_before, self._played_after):
            rows = _rows_of(layout, catalogs, played)
            if rows is not None and rows not in held:
                held.append(rows)

        return held

    def charged(
        self,
        layout: StemLayout,
        catalogs: Mapping[GeneratorClassName, KindCatalog],
        place: int,
        column: Column,
        rows: Rows,
    ) -> Column:
        """The column of the channel at ``place``, each alternative costed with the choice's charges, cheapest first.

        A column scores each alternative at the full cost of the frame with the other channels playing
        the choice ``rows``, so an alternative pays its own channel's charge and the charges of the
        choice's other channels.
        """
        if not self.binding:
            return column

        others = self._paid(layout, catalogs, rows, [index for index in range(len(rows)) if index != place])
        costed = [
            replace(candidate, cost=candidate.cost + others + self._paid_at(place, candidate.instruction))
            for candidate in column
        ]
        return tuple(sorted(costed, key=_cost_of))

    @property
    def _played_before(self) -> Tuple[Optional[InstructionUnion], ...]:
        """What each channel plays the frame before, ``None`` where it pays nothing or the frame lies past the start."""
        return tuple(channel.before if channel is not None else None for channel in self.channels)

    @property
    def _played_after(self) -> Tuple[Optional[InstructionUnion], ...]:
        """What each channel plays the frame after, ``None`` where it pays nothing or the frame lies past the end."""
        return tuple(channel.after if channel is not None else None for channel in self.channels)

    def _paid(
        self,
        layout: StemLayout,
        catalogs: Mapping[GeneratorClassName, KindCatalog],
        rows: Rows,
        places: Sequence[int],
    ) -> float:
        """What the channels at ``places`` pay for playing their rows of ``rows``."""
        return sum(
            self._paid_at(place, catalogs[layout.slots[place].kind].instructions[rows[place]]) for place in places
        )

    def _paid_at(self, place: int, instruction: InstructionUnion) -> float:
        """What the channel at ``place`` pays for playing ``instruction``, nothing where it chooses freely."""
        channel = self.channels[place]
        if channel is None:
            return 0.0

        return channel.charge(instruction)


def _rows_of(
    layout: StemLayout,
    catalogs: Mapping[GeneratorClassName, KindCatalog],
    instructions: Sequence[Optional[InstructionUnion]],
) -> Optional[Rows]:
    """The rows playing ``instructions`` on the stem's channels, ``None`` where a frame lies past the recording."""
    rows: List[int] = []
    for slot, instruction in zip(layout.slots, instructions):
        if instruction is None:
            return None

        rows.append(catalogs[slot.kind].rows_by_instruction[instruction])

    return tuple(rows)


def _reordered(rows: Rows, places: Sequence[int], order: Sequence[int]) -> Rows:
    """``rows`` with the rows at ``places`` taken from ``order``, one for one."""
    reordered = list(rows)
    for target, source in zip(places, order):
        reordered[target] = rows[source]

    return tuple(reordered)


def _cost_of(candidate: ScoredCandidate) -> float:
    return candidate.cost
