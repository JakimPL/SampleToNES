from typing import Dict, Final, Iterable, List, Tuple

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import SINGLE_STATE_LATTICE_WIDTH
from sampletones_core.constants.enums import ChannelName, HierarchyMode
from sampletones_core.fft import Fragment, Window
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import GeneratorUnion
from sampletones_core.library import InstructionLibraryData
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher, ScoredCandidate
from sampletones_core.reconstructions.reconstructor.stems.assignment.frame import assign_frame
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.models.choice import StemChoice
from sampletones_core.reconstructions.reconstructor.stems.models.frame_assignment import StemFrameAssignment

from .conftest import greedy_baseline

RANDOM_SEEDS: Final[Tuple[int, ...]] = (11, 23, 47, 89, 131, 197)


def _config(
    entries: Dict[int, Iterable[ChannelName]],
    levels: List[List[int]],
    mode: HierarchyMode,
    channel_cap: int,
) -> StemsConfig:
    return StemsConfig(
        entries=[StemEntry(id=stem_id, channels=list(channels)) for stem_id, channels in entries.items()],
        hierarchy=StemsHierarchy(levels=levels, mode=mode),
        channel_cap=channel_cap,
    )


class TestSingleStemEquivalence:
    def test_matches_the_greedy_baseline_exactly(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        stems_config = _config({0: channels}, [[0]], HierarchyMode.STRICT, len(channels))

        assignment = assign_frame(
            synthetic_fragment,
            stems_config,
            channels,
            matcher,
            extractor,
            SINGLE_STATE_LATTICE_WIDTH,
        )
        baseline = greedy_baseline(synthetic_fragment, channels, matcher, extractor)

        assert len(assignment.choices) == len(channels)
        assert len(baseline) == len(channels)
        _assert_same_picks(assignment, baseline)

    def test_matches_the_baseline_with_all_four_channels(
        self,
        synthetic_fragment: Fragment,
        all_channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        stems_config = _config({0: all_channels}, [[0]], HierarchyMode.STRICT, len(all_channels))

        assignment = assign_frame(
            synthetic_fragment,
            stems_config,
            all_channels,
            matcher,
            extractor,
            SINGLE_STATE_LATTICE_WIDTH,
        )
        baseline = greedy_baseline(synthetic_fragment, all_channels, matcher, extractor)

        assert len(assignment.choices) == len(all_channels)
        assert len(baseline) == len(all_channels)
        _assert_same_picks(assignment, baseline)


class TestLatticeWidthLeavesOwnership:
    """A wider lattice grows what the decoder may choose from, and the picks stay put."""

    def test_ownership_and_picks_hold_across_widths(
        self,
        synthetic_fragment: Fragment,
        all_channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        stems_config = _config(
            {0: [ChannelName.PULSE1, ChannelName.TRIANGLE], 1: [ChannelName.PULSE2, ChannelName.NOISE]},
            [[0], [1]],
            HierarchyMode.STRICT,
            2,
        )

        narrow = assign_frame(
            synthetic_fragment,
            stems_config,
            all_channels,
            matcher,
            extractor,
            SINGLE_STATE_LATTICE_WIDTH,
        )
        wide = assign_frame(
            synthetic_fragment,
            stems_config,
            all_channels,
            matcher,
            extractor,
            matcher.top_k,
        )

        assert _choice_keys(narrow.choices) == _choice_keys(wide.choices)
        assert narrow.resting == wide.resting
        for narrow_choice, wide_choice in zip(narrow.choices, wide.choices):
            assert narrow_choice.instruction == wide_choice.instruction
            _assert_same_fragment(narrow_choice.approximation, wide_choice.approximation)
            assert len(wide_choice.column) >= len(narrow_choice.column)


class TestStrictDisjointStems:
    def test_matches_sequential_per_subset_baselines(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        subset_pulse_triangle = {
            ChannelName.PULSE1: channels[ChannelName.PULSE1],
            ChannelName.TRIANGLE: channels[ChannelName.TRIANGLE],
        }
        subset_noise = {ChannelName.NOISE: channels[ChannelName.NOISE]}

        baseline_first = greedy_baseline(synthetic_fragment, subset_pulse_triangle, matcher, extractor)
        residual = synthetic_fragment
        for candidate in baseline_first.values():
            residual = extractor.subtract(residual, candidate.approximation)
        baseline_second = greedy_baseline(residual, subset_noise, matcher, extractor)

        expected = dict(baseline_first)
        expected.update(baseline_second)

        stems_config = _config(
            {0: subset_pulse_triangle, 1: subset_noise},
            [[0], [1]],
            HierarchyMode.STRICT,
            len(channels),
        )

        assignment = assign_frame(
            synthetic_fragment,
            stems_config,
            channels,
            matcher,
            extractor,
            SINGLE_STATE_LATTICE_WIDTH,
        )

        assert len(assignment.choices) == len(channels)
        _assert_same_picks(assignment, expected)


class TestRandomizedDifferential:
    @pytest.mark.parametrize("random_seed", RANDOM_SEEDS)
    def test_invariants_and_determinism(
        self,
        random_seed: int,
        config: Config,
        window: Window,
        extractor: FeatureExtractor,
        library_data: InstructionLibraryData,
        all_channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        rng = np.random.default_rng(random_seed)
        fragment = _random_target_fragment(rng, config, window, extractor, library_data)
        stems_config = _random_setup(rng, tuple(all_channels))

        assignment = assign_frame(
            fragment,
            stems_config,
            all_channels,
            matcher,
            extractor,
            SINGLE_STATE_LATTICE_WIDTH,
        )
        repeat = assign_frame(
            fragment,
            stems_config,
            all_channels,
            matcher,
            extractor,
            SINGLE_STATE_LATTICE_WIDTH,
        )

        assert _choice_keys(assignment.choices) == _choice_keys(repeat.choices)
        assert assignment.resting == repeat.resting

        channels_assigned = [choice.channel_name for choice in assignment.choices]
        assert len(channels_assigned) == len(set(channels_assigned))
        assert set(channels_assigned) <= set(all_channels)
        assert set(channels_assigned) | set(assignment.resting) == stems_config.covered_channels

        counts: Dict[int, int] = {}
        for choice in assignment.choices:
            counts[choice.stem_id] = counts.get(choice.stem_id, 0) + 1
            assert choice.channel_name in stems_config.entries_by_id[choice.stem_id].channel_set
        assert all(count <= stems_config.channel_cap for count in counts.values())

        if stems_config.hierarchy.mode == HierarchyMode.STRICT:
            _assert_strict_ordering(assignment, stems_config.hierarchy)


def _assert_same_picks(
    assignment: StemFrameAssignment,
    baseline: Dict[ChannelName, ScoredCandidate],
) -> None:
    assert [choice.channel_name for choice in assignment.choices] == list(baseline.keys())
    assert set(assignment.by_channel) == set(baseline)

    for channel_name, candidate in baseline.items():
        choice = assignment.by_channel[channel_name]
        assert choice.instruction == candidate.instruction
        _assert_same_fragment(choice.approximation, candidate.approximation)


def _assert_same_fragment(left: Fragment, right: Fragment) -> None:
    np.testing.assert_array_equal(np.asarray(left.audio), np.asarray(right.audio))
    np.testing.assert_array_equal(
        np.asarray(left.windowed_audio),
        np.asarray(right.windowed_audio),
    )
    np.testing.assert_array_equal(
        np.asarray(left.feature.values),
        np.asarray(right.feature.values),
    )


def _assert_strict_ordering(
    assignment: StemFrameAssignment,
    hierarchy: StemsHierarchy,
) -> None:
    first_positions = [
        index for index, choice in enumerate(assignment.choices) if choice.stem_id in hierarchy.levels[0]
    ]
    second_positions = [
        index for index, choice in enumerate(assignment.choices) if choice.stem_id in hierarchy.levels[1]
    ]
    if first_positions and second_positions:
        assert max(first_positions) < min(second_positions)


def _choice_keys(choices: Tuple[StemChoice, ...]) -> Tuple[Tuple[int, ChannelName], ...]:
    return tuple((choice.stem_id, choice.channel_name) for choice in choices)


def _random_setup(
    rng: np.random.Generator,
    channel_names: Tuple[ChannelName, ...],
) -> StemsConfig:
    shuffled = list(channel_names)
    rng.shuffle(shuffled)
    split = int(rng.integers(1, len(shuffled)))

    mode = HierarchyMode.ROUND_ROBIN if bool(rng.integers(2)) else HierarchyMode.STRICT
    return _config(
        {0: shuffled[:split], 1: shuffled[split:]},
        [[0], [1]],
        mode,
        int(rng.integers(1, len(channel_names) + 1)),
    )


def _random_target_fragment(
    rng: np.random.Generator,
    config: Config,
    window: Window,
    extractor: FeatureExtractor,
    library_data: InstructionLibraryData,
) -> Fragment:
    instructions = [instruction for instruction in library_data.keys() if library_data[instruction].length > 0]
    audio = np.zeros(window.frame_length, dtype=np.float64)
    for _ in range(int(rng.integers(1, 5))):
        instruction = instructions[int(rng.integers(0, len(instructions)))]
        library_fragment = library_data[instruction]
        shift = int(rng.integers(0, library_fragment.length))
        contribution = library_fragment.get_fragment(shift, config, window)
        audio += np.asarray(contribution.audio) * float(rng.uniform(0.2, 1.0))

    return extractor.extract(audio)[0]
