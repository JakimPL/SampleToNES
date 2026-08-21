from typing import Dict, List, Sequence, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName, HierarchyMode
from sampletones_core.fft import Fragment
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import GeneratorUnion
from sampletones_core.reconstructions.reconstructor.selector.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.assignment.frame import assign_frame
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.models.choice import StemChoice
from sampletones_core.reconstructions.reconstructor.stems.models.frame_assignment import StemFrameAssignment

DEFAULT_CHANNELS: List[ChannelName] = [ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE]


def _config(
    entries: Dict[int, List[ChannelName]],
    levels: List[List[int]],
    mode: HierarchyMode,
    channel_cap: int,
) -> StemsConfig:
    return StemsConfig(
        entries=[StemEntry(id=stem_id, channels=channels) for stem_id, channels in entries.items()],
        hierarchy=StemsHierarchy(levels=levels, mode=mode),
        channel_cap=channel_cap,
    )


def _assign(
    fragment: Fragment,
    stems_config: StemsConfig,
    channels: Dict[ChannelName, GeneratorUnion],
    matcher: FrameMatcher,
    extractor: FeatureExtractor,
) -> StemFrameAssignment:
    return assign_frame(
        fragment,
        stems_config,
        channels,
        matcher,
        extractor,
    )


class TestAssignFrameValidation:
    def test_channel_outside_enabled_channels_raises(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        stems_config = _config({0: [ChannelName.PULSE2]}, [[0]], HierarchyMode.STRICT, 1)
        with pytest.raises(ValueError, match="configuration lacks"):
            _assign(synthetic_fragment, stems_config, channels, matcher, extractor)


class TestFrameCompleteness:
    """Every covered channel leaves the frame either picked or resting, never neither."""

    def test_a_capped_frame_rests_the_channels_no_stem_took(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        stems_config = _config({0: DEFAULT_CHANNELS}, [[0]], HierarchyMode.STRICT, 1)

        assignment = _assign(synthetic_fragment, stems_config, channels, matcher, extractor)

        assert len(assignment.choices) == 1
        assert set(assignment.by_channel) | set(assignment.resting) == stems_config.covered_channels
        assert set(assignment.by_channel).isdisjoint(assignment.resting)

    def test_a_full_frame_rests_nothing(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        stems_config = _config({0: DEFAULT_CHANNELS}, [[0]], HierarchyMode.STRICT, len(DEFAULT_CHANNELS))

        assignment = _assign(synthetic_fragment, stems_config, channels, matcher, extractor)

        assert assignment.resting == ()
        assert set(assignment.by_channel) == stems_config.covered_channels

    def test_a_channel_no_stem_may_occupy_stays_out_of_the_frame(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        stems_config = _config({0: [ChannelName.PULSE1]}, [[0]], HierarchyMode.STRICT, 1)

        assignment = _assign(synthetic_fragment, stems_config, channels, matcher, extractor)

        assert set(assignment.by_channel) == {ChannelName.PULSE1}
        assert assignment.resting == ()


class TestChannelCap:
    def test_strict_mode_respects_the_cap(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        for cap, expected_count in ((1, 1), (2, 2), (5, 3)):
            stems_config = _config({0: DEFAULT_CHANNELS}, [[0]], HierarchyMode.STRICT, cap)
            assignment = _assign(synthetic_fragment, stems_config, channels, matcher, extractor)
            assert len(assignment.choices) == expected_count
            assert {choice.stem_id for choice in assignment.choices} == {0}
            assert len(assignment.resting) == len(DEFAULT_CHANNELS) - expected_count

    def test_round_robin_mode_respects_the_cap(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        stems_config = _config({0: DEFAULT_CHANNELS}, [[0]], HierarchyMode.ROUND_ROBIN, 2)

        assignment = _assign(synthetic_fragment, stems_config, channels, matcher, extractor)

        assert len(assignment.choices) == 2
        assert len(assignment.resting) == 1


class TestTieBreakDeterminism:
    def test_equal_cost_choices_go_to_the_first_stem_in_level_order(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        entries = {0: [ChannelName.PULSE1], 1: [ChannelName.PULSE1]}

        first = _assign(
            synthetic_fragment,
            _config(entries, [[0, 1]], HierarchyMode.STRICT, 1),
            channels,
            matcher,
            extractor,
        )
        assert [(choice.stem_id, choice.channel_name) for choice in first.choices] == [(0, ChannelName.PULSE1)]

        swapped = _assign(
            synthetic_fragment,
            _config(entries, [[1, 0]], HierarchyMode.STRICT, 1),
            channels,
            matcher,
            extractor,
        )
        assert [(choice.stem_id, choice.channel_name) for choice in swapped.choices] == [(1, ChannelName.PULSE1)]

    def test_repeated_runs_give_identical_choices(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        stems_config = _config(
            {0: [ChannelName.PULSE1, ChannelName.TRIANGLE], 1: [ChannelName.NOISE]},
            [[0], [1]],
            HierarchyMode.STRICT,
            2,
        )

        first = _assign(synthetic_fragment, stems_config, channels, matcher, extractor)
        second = _assign(synthetic_fragment, stems_config, channels, matcher, extractor)

        assert _choice_keys(first.choices) == _choice_keys(second.choices)
        assert first.resting == second.resting


class TestHierarchyOrdering:
    def test_strict_mode_exhausts_the_first_level_before_the_next(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        stems_config = _config(
            {0: [ChannelName.PULSE1, ChannelName.TRIANGLE], 1: [ChannelName.NOISE]},
            [[0], [1]],
            HierarchyMode.STRICT,
            2,
        )

        assignment = _assign(synthetic_fragment, stems_config, channels, matcher, extractor)

        assert [choice.stem_id for choice in assignment.choices] == [0, 0, 1]
        assert {choice.channel_name for choice in assignment.choices[:2]} == {
            ChannelName.PULSE1,
            ChannelName.TRIANGLE,
        }
        assert assignment.choices[2].channel_name == ChannelName.NOISE

    def test_round_robin_mode_alternates_levels_each_round(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        stems_config = _config(
            {0: [ChannelName.PULSE1, ChannelName.TRIANGLE], 1: [ChannelName.NOISE]},
            [[0], [1]],
            HierarchyMode.ROUND_ROBIN,
            2,
        )

        assignment = _assign(synthetic_fragment, stems_config, channels, matcher, extractor)

        assert [choice.stem_id for choice in assignment.choices] == [0, 1, 0]
        assert assignment.choices[1].channel_name == ChannelName.NOISE
        assert {assignment.choices[0].channel_name, assignment.choices[2].channel_name} == {
            ChannelName.PULSE1,
            ChannelName.TRIANGLE,
        }
        assert assignment.by_channel.keys() == {
            ChannelName.PULSE1,
            ChannelName.TRIANGLE,
            ChannelName.NOISE,
        }


def _choice_keys(choices: Sequence[StemChoice]) -> Tuple[Tuple[int, ChannelName], ...]:
    return tuple((choice.stem_id, choice.channel_name) for choice in choices)
