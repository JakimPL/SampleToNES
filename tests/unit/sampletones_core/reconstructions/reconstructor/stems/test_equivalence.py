from typing import Dict, Final, Iterable, List, Tuple

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import SINGLE_STATE_LATTICE_WIDTH
from sampletones_core.constants.enums import ChannelName, HierarchyMode, bending_channels
from sampletones_core.fft import Fragment, Window
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import GeneratorUnion
from sampletones_core.library import InstructionLibraryData
from sampletones_core.reconstructions.reconstructor.contribution import Contribution
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher, ScoredCandidate
from sampletones_core.reconstructions.reconstructor.stems.assignment.frame import assign_frame
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_core.reconstructions.reconstructor.stems.models.choice import StemChoice
from sampletones_core.reconstructions.reconstructor.stems.models.frame_assignment import StemFrameAssignment

from .conftest import audible_instruction_of, frame_objective_baseline, rendered_fragment, shared_frames

RANDOM_SEEDS: Final[Tuple[int, ...]] = (11, 23, 47, 89, 131, 197)
COST_TOLERANCE: Final[float] = 1e-5


def _config(
    entries: Dict[int, Iterable[ChannelName]],
    levels: List[List[int]],
    mode: HierarchyMode,
    channel_cap: int,
) -> StemsConfig:
    return StemsConfig(
        entries=[
            StemEntry(
                id=stem_id,
                settings=StemSettings(
                    channels=list(channels),
                    bends=bending_channels(list(channels)),
                    channel_cap=channel_cap,
                ),
            )
            for stem_id, channels in entries.items()
        ],
        hierarchy=StemsHierarchy(levels=levels, mode=mode),
    )


class TestSingleStemEquivalence:
    def test_matches_the_frame_objective_baseline(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        stems_config = _config({0: channels}, [[0]], HierarchyMode.STRICT, len(channels))

        assignment = assign_frame(
            shared_frames(synthetic_fragment, stems_config),
            stems_config,
            channels,
            matcher,
            SINGLE_STATE_LATTICE_WIDTH,
        )
        baseline = frame_objective_baseline(synthetic_fragment, channels, matcher)

        assert [choice.channel_name for choice in assignment.choices] == list(baseline)
        _assert_same_heads(assignment, baseline)

    def test_matches_the_baseline_with_all_four_channels(
        self,
        synthetic_fragment: Fragment,
        all_channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        stems_config = _config({0: all_channels}, [[0]], HierarchyMode.STRICT, len(all_channels))

        assignment = assign_frame(
            shared_frames(synthetic_fragment, stems_config),
            stems_config,
            all_channels,
            matcher,
            SINGLE_STATE_LATTICE_WIDTH,
        )
        baseline = frame_objective_baseline(synthetic_fragment, all_channels, matcher)

        assert [choice.channel_name for choice in assignment.choices] == list(baseline)
        _assert_same_heads(assignment, baseline)

    def test_matches_the_baseline_on_a_frame_two_channels_sound(
        self,
        config: Config,
        extractor: FeatureExtractor,
        library_data: InstructionLibraryData,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        """A frame a pulse and the triangle sound together takes several picks and a second pass."""
        fragment = rendered_fragment(
            config,
            extractor,
            {
                channel_name: audible_instruction_of(library_data, channels[channel_name])
                for channel_name in (ChannelName.PULSE1, ChannelName.TRIANGLE)
            },
        )
        stems_config = _config({0: channels}, [[0]], HierarchyMode.STRICT, len(channels))

        assignment = assign_frame(
            shared_frames(fragment, stems_config),
            stems_config,
            channels,
            matcher,
            SINGLE_STATE_LATTICE_WIDTH,
        )
        baseline = frame_objective_baseline(fragment, channels, matcher)

        assert sum(choice.sounding for choice in assignment.choices) >= 2
        assert [choice.channel_name for choice in assignment.choices] == list(baseline)
        _assert_same_heads(assignment, baseline)


class TestLatticeWidthLeavesOwnership:
    """A wider lattice grows what the decoder may choose from, and the heads stay put."""

    def test_ownership_and_heads_hold_across_widths(
        self,
        synthetic_fragment: Fragment,
        all_channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        stems_config = _config(
            {0: [ChannelName.PULSE1, ChannelName.TRIANGLE], 1: [ChannelName.PULSE2, ChannelName.NOISE]},
            [[0], [1]],
            HierarchyMode.STRICT,
            2,
        )

        narrow = assign_frame(
            shared_frames(synthetic_fragment, stems_config),
            stems_config,
            all_channels,
            matcher,
            SINGLE_STATE_LATTICE_WIDTH,
        )
        wide = assign_frame(
            shared_frames(synthetic_fragment, stems_config),
            stems_config,
            all_channels,
            matcher,
            matcher.top_k,
        )

        assert _choice_keys(narrow.choices) == _choice_keys(wide.choices)
        assert narrow.resting == wide.resting
        for narrow_choice, wide_choice in zip(narrow.choices, wide.choices):
            assert narrow_choice.instruction == wide_choice.instruction
            _assert_same_contribution(narrow_choice.contribution, wide_choice.contribution)
            assert len(wide_choice.column) >= len(narrow_choice.column)


class TestStrictDisjointStems:
    def test_each_stem_answers_its_own_recording(
        self,
        audible_fragments: List[Fragment],
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        """Two stems sounding differently each answer their own frame over their own channels.

        A stem's choices are the frame objective of the sound it contributes, so the channels it
        holds carry that recording and the other stem takes no part in them.
        """
        assert len(audible_fragments) >= 2
        first_fragment, second_fragment = audible_fragments[0], audible_fragments[-1]
        subset_pulse_triangle = {
            ChannelName.PULSE1: channels[ChannelName.PULSE1],
            ChannelName.TRIANGLE: channels[ChannelName.TRIANGLE],
        }
        subset_noise = {ChannelName.NOISE: channels[ChannelName.NOISE]}

        expected = dict(frame_objective_baseline(first_fragment, subset_pulse_triangle, matcher))
        expected.update(frame_objective_baseline(second_fragment, subset_noise, matcher))

        stems_config = _config(
            {0: subset_pulse_triangle, 1: subset_noise},
            [[0], [1]],
            HierarchyMode.STRICT,
            len(channels),
        )

        assignment = assign_frame(
            {0: first_fragment, 1: second_fragment},
            stems_config,
            channels,
            matcher,
            SINGLE_STATE_LATTICE_WIDTH,
        )

        assert set(assignment.by_channel) == set(expected)
        _assert_same_heads(assignment, expected)


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
            shared_frames(fragment, stems_config),
            stems_config,
            all_channels,
            matcher,
            SINGLE_STATE_LATTICE_WIDTH,
        )
        repeat = assign_frame(
            shared_frames(fragment, stems_config),
            stems_config,
            all_channels,
            matcher,
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
            assert choice.channel_name in stems_config.entries_by_id[choice.stem_id].settings.channel_set
        for stem_id, count in counts.items():
            assert count <= stems_config.entries_by_id[stem_id].settings.channel_cap


def _assert_same_heads(
    assignment: StemFrameAssignment,
    baseline: Dict[ChannelName, ScoredCandidate],
) -> None:
    for channel_name, candidate in baseline.items():
        choice = assignment.by_channel[channel_name]
        assert choice.instruction == candidate.instruction
        assert choice.cost == pytest.approx(candidate.cost, abs=COST_TOLERANCE)
        _assert_same_contribution(choice.contribution, candidate.contribution)


def _assert_same_contribution(left: Contribution, right: Contribution) -> None:
    """Two contributions add the same sound: one power, one expected waveform, one variance."""
    np.testing.assert_allclose(left.power, right.power, rtol=1e-6, atol=1e-12)
    np.testing.assert_allclose(left.expectation, right.expectation, rtol=1e-6, atol=1e-9)
    assert left.variance == pytest.approx(right.variance)


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
