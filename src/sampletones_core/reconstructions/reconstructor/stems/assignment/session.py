from typing import Dict, List, Optional, Sequence, Set

from sampletones_core.constants.enums import ChannelName, HierarchyMode
from sampletones_core.fft import Fragment
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import (
    GeneratorUnion,
    get_generator_by_instruction,
    get_remaining_generator_classes,
)
from sampletones_core.reconstructions.reconstructor.selector.matching import (
    FrameMatcher,
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
    ) -> None:
        self.stems_config = stems_config
        self.channels = channels
        self.matcher = matcher
        self.extractor = extractor
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
            resting=tuple(self.free_channels),
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

            choice = self._best_choice(eligible)
            if choice is None:
                return

            self.choices.append(choice)
            self.used_channels[choice.stem_id] += 1
            self.free_channels.remove(choice.channel_name)
            self.residual = self.extractor.subtract(
                self.residual,
                choice.approximation,
            )
            picked_this_visit.add(choice.stem_id)

    def _best_choice(self, stem_ids: Sequence[int]) -> Optional[StemChoice]:
        best: Optional[StemChoice] = None
        for stem_id in stem_ids:
            remaining_channels = self._remaining_channels(stem_id)
            if not remaining_channels:
                continue

            remaining_generator_classes = get_remaining_generator_classes(remaining_channels)
            scored = self.matcher.score_candidates(
                self.residual,
                remaining_generator_classes,
            )
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
        allowed = self.stems_config.entries_by_id[stem_id].channel_set
        return {name: self.channels[name] for name in self.free_channels if name in allowed}
