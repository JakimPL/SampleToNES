from typing import Dict, List, Optional, Sequence, Set, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.fft import Fragment
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import (
    GeneratorUnion,
    get_generator_by_instruction,
    get_remaining_generator_classes,
)

from ..selector.matching import FrameMatcher
from .models import (
    HierarchyMode,
    Stem,
    StemChoice,
    StemFrameAssignment,
    StemHierarchy,
)


def assign_frame(
    fragment: Fragment,
    stems: Dict[int, Stem],
    hierarchy: StemHierarchy,
    channels: Dict[ChannelName, GeneratorUnion],
    matcher: FrameMatcher,
    extractor: FeatureExtractor,
    channel_cap: int,
) -> StemFrameAssignment:
    """
    Assigns one target frame's channels to stems, one pick at a time.

    Every pick scores each eligible stem's candidates against the current residual,
    takes the cheapest choice across the active level, subtracts its approximation
    from the residual, and consumes its channel. Levels pick in the hierarchy's
    mode: round-based gives every level's stems one channel per round in level
    order, strict exhausts each level before the next. Each stem holds at most
    ``channel_cap`` channels per frame.

    Args:
        fragment: The frame to assign, matching the matcher and extractor feature
            space.
        stems: The competing stems keyed by their id.
        hierarchy: The precedence levels and their picking mode.
        channels: The enabled channels with their generators.
        matcher: The candidate scoring machinery.
        extractor: The feature extractor whose subtraction forms the residual.
        channel_cap: The maximum number of channels one stem holds per frame.

    Returns:
        The picks in the order they were made, with the final channel mapping.

    Raises:
        ValueError: If ``channel_cap`` is below 1, a stem allows a channel the
            enabled channels lack, a stem id disagrees with its key, or the
            hierarchy names every stem exactly once.
    """
    _validate(stems, hierarchy, channels, channel_cap)
    session = _AssignmentSession(
        fragment,
        stems,
        hierarchy,
        channels,
        matcher,
        extractor,
        channel_cap,
    )
    return session.run()


def _validate(
    stems: Dict[int, Stem],
    hierarchy: StemHierarchy,
    channels: Dict[ChannelName, GeneratorUnion],
    channel_cap: int,
) -> None:
    if channel_cap < 1:
        raise ValueError("channel_cap must be at least 1")

    enabled = set(channels)
    for stem_id, stem in stems.items():
        if stem.id != stem_id:
            raise ValueError(f"Stem {stem.id} is keyed as {stem_id}")

        foreign = set(stem.channels) - enabled
        if foreign:
            raise ValueError(f"Stem {stem.id} allows channels the configuration lacks: {sorted(foreign)}")

    referenced = [stem_id for level in hierarchy.levels for stem_id in level]
    if set(referenced) != set(stems) or len(set(referenced)) != len(referenced):
        raise ValueError("Hierarchy levels must name every stem exactly once")


class _AssignmentSession:
    """
    Carries one frame assignment's mutable progress: the residual, the free
    channels, and the per-stem channel counts.
    """

    def __init__(
        self,
        fragment: Fragment,
        stems: Dict[int, Stem],
        hierarchy: StemHierarchy,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
        channel_cap: int,
    ) -> None:
        self.stems = stems
        self.hierarchy = hierarchy
        self.channels = channels
        self.matcher = matcher
        self.extractor = extractor
        self.channel_cap = channel_cap
        self.residual = fragment
        reachable = {channel for stem in stems.values() for channel in stem.channels}
        self.free_channels = [name for name in ChannelName.items() if name in reachable]
        self.used_channels: Dict[int, int] = {stem_id: 0 for stem_id in stems}
        self.choices: List[StemChoice] = []

    def run(self) -> StemFrameAssignment:
        match self.hierarchy.mode:
            case HierarchyMode.ROUND_ROBIN:
                self._round_robin()
            case HierarchyMode.STRICT:
                self._strict()
        return StemFrameAssignment(tuple(self.choices))

    def _round_robin(self) -> None:
        for _ in range(self.channel_cap):
            for level in self.hierarchy.levels:
                if not self.free_channels:
                    return
                self._pick_from_level(level, repeat=False)

    def _strict(self) -> None:
        for level in self.hierarchy.levels:
            if not self.free_channels:
                return
            self._pick_from_level(level, repeat=True)

    def _pick_from_level(self, level: Tuple[int, ...], *, repeat: bool) -> None:
        picked_this_visit: Set[int] = set()
        while True:
            eligible = [
                stem_id
                for stem_id in level
                if self.used_channels[stem_id] < self.channel_cap and (repeat or stem_id not in picked_this_visit)
            ]
            if not eligible or not self.free_channels:
                return

            choice = self._best_choice(eligible)
            if choice is None:
                return

            self.choices.append(choice)
            self.used_channels[choice.stem_id] += 1
            self.free_channels.remove(choice.channel_name)
            self.residual = self.extractor.subtract(self.residual, choice.approximation)
            picked_this_visit.add(choice.stem_id)

    def _best_choice(self, stem_ids: Sequence[int]) -> Optional[StemChoice]:
        best: Optional[StemChoice] = None
        for stem_id in stem_ids:
            remaining_channels = self._remaining_channels(stem_id)
            if not remaining_channels:
                continue

            remaining_generator_classes = get_remaining_generator_classes(remaining_channels)
            scored = self.matcher.score_candidates(self.residual, remaining_generator_classes)
            candidate = scored[0]
            generator = get_generator_by_instruction(
                candidate.instruction,
                remaining_generator_classes,
            )
            choice = StemChoice(
                stem_id=stem_id,
                channel_name=ChannelName(generator.name),
                instruction=candidate.instruction,
                approximation=candidate.approximation,
                cost=candidate.cost,
            )
            if best is None or choice.cost < best.cost:
                best = choice
        return best

    def _remaining_channels(
        self,
        stem_id: int,
    ) -> Dict[ChannelName, GeneratorUnion]:
        return {name: self.channels[name] for name in self.free_channels if name in self.stems[stem_id].channels}
