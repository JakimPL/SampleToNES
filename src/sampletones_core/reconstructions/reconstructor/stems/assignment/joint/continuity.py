from dataclasses import dataclass, replace
from typing import List, Mapping, Optional, Self, Sequence, Tuple

from sampletones_core.constants.enums import ChannelName, GeneratorClassName
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

Neighbors = Tuple[Optional[InstructionUnion], ...]


@dataclass(frozen=True)
class ChannelContinuity:
    """What a channel plays in the frames on either side of a frame, and what the frame pays to break with it.

    The analysis window averages a channel over several frames, so a channel switched on and off
    from frame to frame reads as a level between the two, which the ear hears as flicker. A frame's
    choice pays ``inertia`` times the decoder's charges for the channel changing from what the frame
    before plays and to what the frame after plays. A frame at either end of the recording has one
    neighbor and answers to it alone.

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
        """The continuity of ``line`` around ``frame``, its neighbors as the line plays them now."""
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

    A combination pays what its channels' charges add up to. Pulses the stem drives alike sound the
    same on either channel, so a combination pays for the order of its pulses that breaks least. A
    channel with no continuity chooses freely and pays nothing, and a stem whose channels all choose
    freely, as a frame heard alone does, leaves every cost as the criterion reads it.

    Attributes:
        layout: The stem's channels.
        catalogs: Each kind's rows.
        channels: Each channel's continuity, in the layout's channel order, ``None`` where the channel
            chooses freely.
    """

    layout: StemLayout
    catalogs: Mapping[GeneratorClassName, KindCatalog]
    channels: Tuple[Optional[ChannelContinuity], ...]

    @classmethod
    def free(cls, layout: StemLayout, catalogs: Mapping[GeneratorClassName, KindCatalog]) -> Self:
        """A stem whose frame chooses freely of the frames beside it."""
        return cls(layout=layout, catalogs=catalogs, channels=(None,) * len(layout.slots))

    @classmethod
    def of(
        cls,
        layout: StemLayout,
        catalogs: Mapping[GeneratorClassName, KindCatalog],
        continuity: Mapping[ChannelName, ChannelContinuity],
    ) -> Self:
        """The stem's part of ``continuity``, which holds every channel the stem may sound."""
        return cls(
            layout=layout, catalogs=catalogs, channels=tuple(continuity[slot.channel_name] for slot in layout.slots)
        )

    @property
    def binding(self) -> bool:
        """Whether a combination pays anything for breaking with the frames beside the frame."""
        return any(channel is not None and channel.inertia > 0 for channel in self.channels)

    def charge(self, rows: Rows) -> float:
        """What the frame pays for sounding ``rows`` beside the frames around it, its pulses ordered to break least."""
        if not self.binding:
            return 0.0

        every_place = range(len(self.layout.slots))
        return min(self._paid(ordered, every_place) for ordered in self.layout.pulse_orders(rows))

    def beside(self) -> List[Rows]:
        """The combinations the frame before and the frame after play, each once, which a frame may hold through.

        A frame at either end of the recording has one of them.
        """
        if not self.binding:
            return []

        held: List[Rows] = []
        for played in (self._played_before, self._played_after):
            rows = self._rows_playing(played)
            if rows is not None and rows not in held:
                held.append(rows)

        return held

    def charged(self, place: int, column: Column, rows: Rows) -> Column:
        """The column of the channel at ``place``, each alternative costed with the choice's charges, cheapest first.

        A column scores each alternative at the full cost of the frame with the other channels playing
        the choice ``rows``, so an alternative pays its own channel's charge and the charges of the
        choice's other channels, each on the channel the choice plays it on.
        """
        if not self.binding:
            return column

        others = self._paid(rows, [index for index in range(len(rows)) if index != place])
        costed = [
            replace(candidate, cost=candidate.cost + others + self._paid_at(place, candidate.instruction))
            for candidate in column
        ]
        return tuple(sorted(costed, key=_cost_of))

    @property
    def _played_before(self) -> Neighbors:
        """What each channel plays the frame before, ``None`` where it chooses freely or the recording starts."""
        return tuple(channel.before if channel is not None else None for channel in self.channels)

    @property
    def _played_after(self) -> Neighbors:
        """What each channel plays the frame after, ``None`` where it chooses freely or the recording ends."""
        return tuple(channel.after if channel is not None else None for channel in self.channels)

    def _rows_playing(self, played: Neighbors) -> Optional[Rows]:
        """The rows playing ``played`` on the stem's channels, ``None`` where a channel plays nothing known there."""
        rows: List[int] = []
        for slot, instruction in zip(self.layout.slots, played):
            if instruction is None:
                return None

            rows.append(self.catalogs[slot.kind].rows_by_instruction[instruction])

        return tuple(rows)

    def _paid(self, rows: Rows, places: Sequence[int]) -> float:
        """What the channels at ``places`` pay for playing their rows of ``rows``."""
        return sum(self._paid_at(place, self._instruction(place, rows[place])) for place in places)

    def _paid_at(self, place: int, instruction: InstructionUnion) -> float:
        """What the channel at ``place`` pays for playing ``instruction``, nothing where it chooses freely."""
        channel = self.channels[place]
        if channel is None:
            return 0.0

        return channel.charge(instruction)

    def _instruction(self, place: int, row: int) -> InstructionUnion:
        """What ``row`` plays on the channel at ``place``."""
        return self.catalogs[self.layout.slots[place].kind].instructions[row]


def _cost_of(candidate: ScoredCandidate) -> float:
    return candidate.cost
