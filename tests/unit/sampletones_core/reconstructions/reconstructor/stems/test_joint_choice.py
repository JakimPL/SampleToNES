from typing import Any, Dict, Final, FrozenSet, List, Set, Tuple

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.fft import Fragment, Window
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import GeneratorUnion, get_generators_by_channels
from sampletones_core.instructions import InstructionUnion, PulseInstruction
from sampletones_core.library import InstructionLibraryData, InstructionLibraryFragment
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint import choice
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.catalog import KindCatalog
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.choice import (
    CombinationJudge,
    ScoredCombination,
)
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.combinations import CombinationSearch, Rows
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.fit import FitTarget
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.hearing import SteadyHearing
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.layout import StemLayout, separate_layouts
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_core.reconstructions.reconstructor.worker import ReconstructorWorker
from sampletones_shared.array import to_numpy

from ..conftest import JOINT_SIGNAL_LENGTH, rendered_fragment

PULSES: Final[List[ChannelName]] = [ChannelName.PULSE1, ChannelName.PULSE2]
PITCHES: Final[FrozenSet[int]] = frozenset({64, 67})
VOLUMES: Final[FrozenSet[int]] = frozenset({4, 8, 12})
DUTY_CYCLES: Final[FrozenSet[int]] = frozenset({1, 3})
PITCH: Final[int] = 64
OTHER_PITCH: Final[int] = 67
LOUD: Final[int] = 12
HALF: Final[int] = 8
QUIET: Final[int] = 4
WRITTEN_DUTY: Final[int] = 1
MIRRORED_DUTY: Final[int] = 3
EXACT_TOLERANCE: Final[float] = 0.0


def _pulse(pitch: int, volume: int, duty_cycle: int) -> PulseInstruction:
    return PulseInstruction(on=True, pitch=pitch, volume=volume, duty_cycle=duty_cycle)


@pytest.fixture(name="pulse_channels", scope="module")
def pulse_channels_fixture(config: Config) -> Dict[ChannelName, GeneratorUnion]:
    return get_generators_by_channels(config, PULSES)


@pytest.fixture(name="duty_matcher", scope="module")
def duty_matcher_fixture(
    config: Config,
    window: Window,
    extractor: FeatureExtractor,
    pulse_channels: Dict[ChannelName, GeneratorUnion],
) -> FrameMatcher:
    """The matcher of a library of two pulse notes on the two duty cycles sharing a spectrum."""
    generator = pulse_channels[ChannelName.PULSE1]
    data: Dict[InstructionUnion, InstructionLibraryFragment[Any]] = {}
    for instruction in generator.get_possible_instructions():
        kept = not instruction.on or (
            isinstance(instruction, PulseInstruction)
            and instruction.pitch in PITCHES
            and instruction.volume in VOLUMES
            and instruction.duty_cycle in DUTY_CYCLES
        )
        if kept:
            data[instruction] = InstructionLibraryFragment.create(generator, instruction, extractor)

    return ReconstructorWorker(
        config=config,
        window=window,
        channels=pulse_channels,
        library_data=InstructionLibraryData.create(config, data),
        signal_length=JOINT_SIGNAL_LENGTH,
    ).matcher


class _Judging:
    """A frame of one held pulse note, with the search and the judge of a stem holding both pulses."""

    def __init__(
        self,
        config: Config,
        extractor: FeatureExtractor,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        self.fragment: Fragment = rendered_fragment(
            config, extractor, {ChannelName.PULSE1: _pulse(PITCH, LOUD, WRITTEN_DUTY)}
        )
        self.layout: StemLayout = separate_layouts(StemsConfig.single_entry(StemSettings.covering(PULSES)), channels)[0]
        generator = channels[ChannelName.PULSE1]
        self.catalog = KindCatalog.build(matcher.candidate_provider, generator)
        catalogs = {GeneratorClassName.PULSE_GENERATOR: self.catalog}
        weights = np.asarray(to_numpy(matcher.scorer.criterion.weights), dtype=np.float64).reshape(-1)
        target = FitTarget.of(self.fragment, matcher.scorer.criterion)
        hearing = SteadyHearing(layout=self.layout, catalogs=catalogs, bins=len(self.fragment.feature.values))
        self.search = CombinationSearch(self.fragment, target, self.layout, catalogs, matcher, hearing)
        self.judge = CombinationJudge(self.fragment, self.layout, catalogs, matcher, weights, hearing)

    def row(self, instruction: PulseInstruction) -> int:
        return self.catalog.instructions.index(instruction)

    def best(self, candidates: List[Rows]) -> ScoredCombination:
        return self.judge.best(self.search, self.judge.finalists(candidates))

    def sounding(self, combination: ScoredCombination) -> Set[Tuple[int, int, int]]:
        """The pitch, volume and duty cycle of every pulse the combination sounds."""
        sounded: Set[Tuple[int, int, int]] = set()
        for row in combination.rows:
            instruction = self.catalog.instructions[row]
            if isinstance(instruction, PulseInstruction) and instruction.on:
                sounded.add((instruction.pitch, instruction.volume, instruction.duty_cycle))
        return sounded


@pytest.fixture(name="judging", scope="module")
def judging_fixture(
    config: Config,
    extractor: FeatureExtractor,
    pulse_channels: Dict[ChannelName, GeneratorUnion],
    duty_matcher: FrameMatcher,
) -> _Judging:
    return _Judging(config, extractor, pulse_channels, duty_matcher)


class TestTheCombinationJudge:
    def test_a_quiet_pulse_the_frame_lacks_is_silenced(self, judging: _Judging) -> None:
        extra = (judging.row(_pulse(PITCH, LOUD, WRITTEN_DUTY)), judging.row(_pulse(OTHER_PITCH, QUIET, WRITTEN_DUTY)))

        best = judging.best([extra])

        assert judging.sounding(best) == {(PITCH, LOUD, WRITTEN_DUTY)}

    def test_a_note_split_over_both_pulses_gathers_on_one_at_the_volume_it_sounds(self, judging: _Judging) -> None:
        half = judging.row(_pulse(PITCH, HALF, WRITTEN_DUTY))

        best = judging.best([(half, half)])

        assert judging.sounding(best) == {(PITCH, LOUD, WRITTEN_DUTY)}
        assert sum(judging.catalog.sounding(row) for row in best.rows) == 1

    def test_a_pulse_tries_the_duty_cycle_sharing_its_spectrum_however_far_the_spectral_term_sets_them(
        self, judging: _Judging, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(choice, "TIMBRE_TOLERANCE", EXACT_TOLERANCE)
        mirrored = (judging.row(_pulse(PITCH, LOUD, MIRRORED_DUTY)), judging.catalog.silence)

        best = judging.best([mirrored])

        assert judging.sounding(best) == {(PITCH, LOUD, WRITTEN_DUTY)}
