from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Sequence, Set, Tuple

import numpy as np

from sampletones_core.constants.algorithm import RESTING_FRAME_COST, STEM_ACTIVITY_FLOOR
from sampletones_core.constants.enums import (
    ChannelName,
    GeneratorClassName,
    HierarchyMode,
)
from sampletones_core.fft import Fragment
from sampletones_core.generators import GeneratorUnion, get_remaining_generator_classes
from sampletones_core.reconstructions.reconstructor.contribution import Contribution
from sampletones_core.reconstructions.reconstructor.matching import (
    Column,
    FrameMatcher,
    ScoredCandidate,
    column_of,
)
from sampletones_core.reconstructions.reconstructor.mix import FrameMix
from sampletones_core.reconstructions.reconstructor.stems.configs.config import (
    StemsConfig,
)
from sampletones_core.reconstructions.reconstructor.stems.models.choice import (
    StemChoice,
)
from sampletones_core.reconstructions.reconstructor.stems.models.frame_assignment import (
    StemFrameAssignment,
)
from sampletones_core.reconstructions.reconstructor.stems.models.rest import StemRest
from sampletones_shared.array import to_numpy


@dataclass(frozen=True)
class StemOffer:
    """What one stem offers for a channel: that channel's column in the stem's frame, and what its head saves.

    The column arrives best first, so its head is the candidate the stem competes with.

    Attributes:
        stem_id: The stem making the offer.
        generator: The generator standing for the channel the stem would take.
        column: The channel's candidates scored in the stem's frame, best first.
        improvement: How far the head lowers the stem's frame cost, weighted by the energy of the
            stem's frame.
    """

    stem_id: int
    generator: GeneratorUnion
    column: Column
    improvement: float

    @property
    def head(self) -> ScoredCandidate:
        return self.column[0]


@dataclass(frozen=True)
class ScoredChoice:
    """A choice together with the contributions sounding beside it when its column was scored."""

    choice: StemChoice
    context: Tuple[Contribution, ...]


class AssignmentSession:
    """
    Carries one frame assignment's mutable progress: each stem's mix and frame cost, the free
    channels, and the per-stem channel counts.

    A stem's mix is what its picks sound in its own frame, so a candidate is scored by the cost
    that frame reaches with the candidate sounding beside them, and the channel's silence is one
    of the candidates. A channel is taken where it lowers a frame's cost, by the stem whose sound
    it covers most. Only the free channels are shared: the stems compete for them, ordered by the
    hierarchy, and the stems sounding in the frame are the ones that compete.
    """

    def __init__(
        self,
        fragments: Dict[int, Fragment],
        stems_config: StemsConfig,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        lattice_width: int,
    ) -> None:
        self.fragments = fragments
        self.stems_config = stems_config
        self.channels = channels
        self.matcher = matcher
        self.lattice_width = lattice_width
        self.channel_cap = stems_config.channel_cap
        covered = stems_config.covered_channels
        self.free_channels = [name for name in ChannelName.items() if name in covered]
        self.used_channels: Dict[int, int] = {entry.id: 0 for entry in stems_config.entries}
        self.sounding = self._sounding_stems()
        self.mixes: Dict[int, FrameMix] = {stem_id: FrameMix.empty(fragments[stem_id]) for stem_id in self.sounding}
        self.frame_costs: Dict[int, float] = {
            stem_id: matcher.mix_cost(fragments[stem_id], mix) for stem_id, mix in self.mixes.items()
        }
        self.energies: Dict[int, float] = {
            stem_id: matcher.reference_energy(fragments[stem_id]) for stem_id in self.sounding
        }
        self.columns: Dict[Tuple[int, GeneratorClassName], Column] = {}
        self.choices: List[ScoredChoice] = []

    def run(self) -> StemFrameAssignment:
        """Runs the frame's picks, settles the channels no pick took, and reports the frame whole."""
        match self.stems_config.hierarchy.mode:
            case HierarchyMode.ROUND_ROBIN:
                self._round_robin()
            case HierarchyMode.STRICT:
                self._strict()

        self._settle_declined()
        self._sweep()
        return StemFrameAssignment(
            choices=tuple(
                StemChoice(
                    stem_id=scored.choice.stem_id,
                    channel_name=scored.choice.channel_name,
                    column=column_of(scored.choice.column, self.lattice_width),
                )
                for scored in self.choices
            ),
            rests=self._rests(),
        )

    def _round_robin(self) -> None:
        for _ in range(self.channel_cap):
            for level in self.stems_config.hierarchy.levels:
                if not self.free_channels:
                    return

                self._pick_from_level(level, repeat=False)

    def _strict(self) -> None:
        for level in self.stems_config.hierarchy.levels:
            if not self.free_channels:
                return

            self._pick_from_level(level, repeat=True)

    def _pick_from_level(
        self,
        level: Sequence[int],
        *,
        repeat: bool,
    ) -> None:
        picked_this_visit: Set[int] = set()
        while True:
            eligible = [
                stem_id
                for stem_id in level
                if stem_id in self.sounding
                and self.used_channels[stem_id] < self.channel_cap
                and (repeat or stem_id not in picked_this_visit)
            ]
            if not eligible or not self.free_channels:
                return

            offer = self._best_offer(eligible)
            if offer is None:
                return

            self._take(offer)
            picked_this_visit.add(offer.stem_id)

    def _best_offer(self, stem_ids: Sequence[int]) -> Optional[StemOffer]:
        """The offer lowering its stem's frame cost the most, weighted by that frame's energy.

        A cost is a fraction of its own frame's energy, so two stems' costs stand on different
        scales; weighting a lowering by the energy behind it states it in absolute terms, so the
        channel reaches the stem whose sound it covers most. An offer whose head is the channel's
        silence, or which lowers nothing, stands aside. Equal offers leave the one already
        standing, which is earlier in level order and then in channel order, so a rerun of the
        same frame assigns the same way.
        """
        best: Optional[StemOffer] = None
        for stem_id in stem_ids:
            remaining_generator_classes = get_remaining_generator_classes(self._remaining_channels(stem_id))
            for generator in remaining_generator_classes.values():
                column = self._column(stem_id, generator)
                head = column[0]
                improvement = (self.frame_costs[stem_id] - head.cost) * self.energies[stem_id]
                if not head.instruction.on or improvement <= 0.0:
                    continue

                if best is None or improvement > best.improvement:
                    best = StemOffer(stem_id=stem_id, generator=generator, column=column, improvement=improvement)

        return best

    def _take(self, offer: StemOffer) -> None:
        """Gives the offer's channel to its stem, sounding the head in that stem's mix."""
        stem_id = offer.stem_id
        self._record(stem_id, ChannelName(offer.generator.name), offer.column)
        self.mixes[stem_id] = self.mixes[stem_id].added(offer.head.contribution)
        self.frame_costs[stem_id] = offer.head.cost
        self._forget_columns(stem_id)

    def _settle_declined(self) -> None:
        """Gives each channel no pick took to the first sounding stem that may still hold it.

        The channel sounds nothing there, and its column keeps the alternatives a decoder may
        still sound when the frames around ask for the channel. A declined channel counts against
        the stem's cap, so no decoded frame sounds more channels than the cap allows. A channel no
        stem may hold stays free for the rests.
        """
        for channel_name in list(self.free_channels):
            stem_id = self._settling_stem(channel_name)
            if stem_id is None:
                continue

            self._record(stem_id, channel_name, self._column(stem_id, self.channels[channel_name]))

    def _sweep(self) -> None:
        """Scores every choice once more with the stem's other choices sounding beside it.

        A pick is made before the picks after it, so the channels taken early answered a frame the
        later channels had yet to join. Scoring each channel again against what the others settled
        on lets its head move to what the whole frame asks of it: a channel may fall silent where
        the others cover its sound, or sound where they leave room. A choice whose context is
        unchanged keeps its column.
        """
        for index, scored in enumerate(self.choices):
            stem_id = scored.choice.stem_id
            context = tuple(
                other.choice.head.contribution
                for other_index, other in enumerate(self.choices)
                if other_index != index and other.choice.stem_id == stem_id and other.choice.sounding
            )
            if len(context) == len(scored.context) and all(
                current is previous for current, previous in zip(context, scored.context)
            ):
                continue

            fragment = self.fragments[stem_id]
            column = self.matcher.score_column(
                fragment,
                self.channels[scored.choice.channel_name],
                FrameMix.of(fragment, context),
            )
            self.choices[index] = ScoredChoice(
                choice=StemChoice(stem_id=stem_id, channel_name=scored.choice.channel_name, column=column),
                context=context,
            )

    def _record(self, stem_id: int, channel_name: ChannelName, column: Column) -> None:
        context = tuple(
            scored.choice.head.contribution
            for scored in self.choices
            if scored.choice.stem_id == stem_id and scored.choice.sounding
        )
        self.choices.append(
            ScoredChoice(
                choice=StemChoice(stem_id=stem_id, channel_name=channel_name, column=column),
                context=context,
            )
        )
        self.used_channels[stem_id] += 1
        self.free_channels.remove(channel_name)

    def _column(self, stem_id: int, generator: GeneratorUnion) -> Column:
        """The column of ``generator``'s class in the stem's frame, scored once per mix."""
        key = (stem_id, generator.class_name())
        column = self.columns.get(key)
        if column is None:
            column = self.matcher.score_column(self.fragments[stem_id], generator, self.mixes[stem_id])
            self.columns[key] = column

        return column

    def _forget_columns(self, stem_id: int) -> None:
        for key in [key for key in self.columns if key[0] == stem_id]:
            del self.columns[key]

    def _settling_stem(self, channel_name: ChannelName) -> Optional[int]:
        """The first sounding stem in hierarchy order that allows ``channel_name`` and has cap left."""
        for level in self.stems_config.hierarchy.levels:
            for stem_id in level:
                allowed = self.stems_config.entries_by_id[stem_id].settings.channel_set
                if (
                    stem_id in self.sounding
                    and channel_name in allowed
                    and self.used_channels[stem_id] < self.channel_cap
                ):
                    return stem_id

        return None

    def _rests(self) -> Tuple[StemRest, ...]:
        """The channels no stem holds, each holding its null instruction over a silent frame."""
        if not self.free_channels:
            return ()

        fragment = next(iter(self.fragments.values()))
        silence = Contribution.silence(len(fragment.feature.values), fragment.audio.shape[0])
        return tuple(
            StemRest(
                channel_name=channel_name,
                column=(
                    ScoredCandidate(
                        instruction=self.channels[channel_name].get_instruction_type().null_instruction(),
                        cost=RESTING_FRAME_COST,
                        contribution=silence,
                    ),
                ),
            )
            for channel_name in self.free_channels
        )

    def _sounding_stems(self) -> FrozenSet[int]:
        """The stems whose own frame reaches a level a channel can render.

        A frame quieter than the quietest note the hardware plays, measured against the working
        level, holds nothing for a channel to sound. Its stem stands aside, so the channel goes
        to a stem that does sound there or rests, and a recording silent through a passage keeps
        that passage silent on the channels it holds.
        """
        return frozenset(
            stem_id
            for stem_id, fragment in self.fragments.items()
            if float(np.max(np.abs(to_numpy(fragment.audio)), initial=0.0)) >= STEM_ACTIVITY_FLOOR
        )

    def _remaining_channels(
        self,
        stem_id: int,
    ) -> Dict[ChannelName, GeneratorUnion]:
        allowed = self.stems_config.entries_by_id[stem_id].settings.channel_set
        return {name: self.channels[name] for name in self.free_channels if name in allowed}
