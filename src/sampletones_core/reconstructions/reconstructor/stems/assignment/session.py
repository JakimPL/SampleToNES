from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Set, Tuple

from sampletones_core.constants.algorithm import (
    RESTING_FRAME_COST,
    SINGLE_STATE_LATTICE_WIDTH,
)
from sampletones_core.constants.enums import (
    ChannelName,
    GeneratorClassName,
    HierarchyMode,
)
from sampletones_core.fft import Fragment
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import (
    GeneratorUnion,
    get_generator_by_instruction,
    get_remaining_generator_classes,
)
from sampletones_core.reconstructions.reconstructor.matching import (
    Column,
    FrameMatcher,
    ScoredCandidate,
)
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


@dataclass(frozen=True)
class StemOffer:
    """What one stem offers for the current residual: a shortlist, and the channel it won with.

    The shortlist arrives best first, so its head is the candidate the stem competes with, and
    the generator behind that head names the channel the stem would take.
    """

    stem_id: int
    generator: GeneratorUnion
    shortlist: Tuple[ScoredCandidate, ...]
    generator_classes: Dict[GeneratorClassName, GeneratorUnion]

    @property
    def candidate(self) -> ScoredCandidate:
        return self.shortlist[0]

    @property
    def class_restricted(self) -> bool:
        """The shortlist covers this offer's generator class alone, so it is the channel's own column."""
        return len(self.generator_classes) == 1


class AssignmentSession:
    """
    Carries one frame assignment's mutable progress: the residual, the free
    channels, and the per-stem channel counts.
    """

    def __init__(
        self,
        fragment: Fragment,
        stems_config: StemsConfig,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
        lattice_width: int,
    ) -> None:
        self.fragment = fragment
        self.stems_config = stems_config
        self.channels = channels
        self.matcher = matcher
        self.extractor = extractor
        self.lattice_width = lattice_width
        self.channel_cap = stems_config.channel_cap
        self.residual = fragment
        covered = stems_config.covered_channels
        self.free_channels = [name for name in ChannelName.items() if name in covered]
        self.used_channels: Dict[int, int] = {entry.id: 0 for entry in stems_config.entries}
        self.choices: List[StemChoice] = []

    def run(self) -> StemFrameAssignment:
        """Runs the frame's picks and reports them together with the channels left resting."""
        match self.stems_config.hierarchy.mode:
            case HierarchyMode.ROUND_ROBIN:
                self._round_robin()
            case HierarchyMode.STRICT:
                self._strict()

        return StemFrameAssignment(
            choices=tuple(self.choices),
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
                if self.used_channels[stem_id] < self.channel_cap and (repeat or stem_id not in picked_this_visit)
            ]
            if not eligible or not self.free_channels:
                return

            offer = self._best_offer(eligible)
            if offer is None:
                return

            choice = self._choice(offer)
            self.choices.append(choice)
            self.used_channels[choice.stem_id] += 1
            self.free_channels.remove(choice.channel_name)
            self.residual = self.extractor.subtract(
                self.residual,
                choice.approximation,
            )
            picked_this_visit.add(choice.stem_id)

    def _best_offer(self, stem_ids: Sequence[int]) -> Optional[StemOffer]:
        best: Optional[StemOffer] = None
        for stem_id in stem_ids:
            remaining_channels = self._remaining_channels(stem_id)
            if not remaining_channels:
                continue

            remaining_generator_classes = get_remaining_generator_classes(remaining_channels)
            scored = self.matcher.score_candidates(
                self.residual,
                remaining_generator_classes,
            )
            offer = StemOffer(
                stem_id=stem_id,
                generator=get_generator_by_instruction(
                    scored[0].instruction,
                    remaining_generator_classes,
                ),
                shortlist=tuple(scored),
                generator_classes=remaining_generator_classes,
            )
            if best is None or offer.candidate.cost < best.candidate.cost:
                best = offer

        return best

    def _choice(self, offer: StemOffer) -> StemChoice:
        return StemChoice(
            stem_id=offer.stem_id,
            channel_name=ChannelName(offer.generator.name),
            instruction=offer.candidate.instruction,
            approximation=offer.candidate.approximation,
            cost=offer.candidate.cost,
            column=self._column(offer),
        )

    def _column(self, offer: StemOffer) -> Column:
        """The alternatives the decoder chooses among for the channel this offer won.

        A decoder reading one candidate per frame settles on the pick itself, so the frame is
        answered by the scoring already done. A wider lattice scores the winning channel's own
        candidates against the same residual, which reaches the alternatives a scoring across
        several channels ranked below other channels' candidates. Where the offer was already
        scored over one generator class, that scoring is the column.
        """
        if self.lattice_width == SINGLE_STATE_LATTICE_WIDTH:
            return (offer.candidate,)

        if offer.class_restricted:
            return offer.shortlist[: self.lattice_width]

        generator = offer.generator
        scored = self.matcher.score_candidates(
            self.residual,
            {generator.class_name(): generator},
        )
        return tuple(scored[: self.lattice_width])

    def _rests(self) -> Tuple[StemRest, ...]:
        """The channels no stem took, each holding its null instruction over a silent frame."""
        if not self.free_channels:
            return ()

        silent = self.fragment * 0.0
        return tuple(
            StemRest(
                channel_name=channel_name,
                column=(self._resting_candidate(channel_name, silent),),
            )
            for channel_name in self.free_channels
        )

    def _resting_candidate(self, channel_name: ChannelName, silent: Fragment) -> ScoredCandidate:
        instruction = self.channels[channel_name].get_instruction_type().null_instruction()
        return ScoredCandidate(
            instruction=instruction,
            cost=RESTING_FRAME_COST,
            approximation=silent,
        )

    def _remaining_channels(
        self,
        stem_id: int,
    ) -> Dict[ChannelName, GeneratorUnion]:
        allowed = self.stems_config.entries_by_id[stem_id].channel_set
        return {name: self.channels[name] for name in self.free_channels if name in allowed}
