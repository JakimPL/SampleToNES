from typing import Dict, FrozenSet, Sequence, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.fft import Fragment
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import GeneratorUnion
from sampletones_core.reconstructions.reconstructor.selector.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems import (
    HierarchyMode,
    Stem,
    StemChoice,
    StemFrameAssignment,
    StemHierarchy,
    assign_frame,
)

DEFAULT_CHANNELS: FrozenSet[ChannelName] = frozenset((ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE))


def _assign(
    fragment: Fragment,
    stems: Dict[int, Stem],
    hierarchy: StemHierarchy,
    channels: Dict[ChannelName, GeneratorUnion],
    matcher: FrameMatcher,
    extractor: FeatureExtractor,
    channel_cap: int,
) -> StemFrameAssignment:
    return assign_frame(
        fragment,
        stems,
        hierarchy,
        channels,
        matcher,
        extractor,
        channel_cap,
    )


class TestAssignFrameValidation:
    def test_zero_cap_raises(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        stems = {0: Stem(id=0, channels=DEFAULT_CHANNELS)}
        hierarchy = StemHierarchy(levels=((0,),), mode=HierarchyMode.STRICT)
        with pytest.raises(ValueError, match="channel_cap"):
            _assign(synthetic_fragment, stems, hierarchy, channels, matcher, extractor, 0)

    def test_stem_id_disagreeing_with_its_key_raises(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        stems = {0: Stem(id=1, channels=DEFAULT_CHANNELS)}
        hierarchy = StemHierarchy(levels=((0,),), mode=HierarchyMode.STRICT)
        with pytest.raises(ValueError, match="keyed"):
            _assign(synthetic_fragment, stems, hierarchy, channels, matcher, extractor, 1)

    def test_channel_outside_enabled_channels_raises(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        stems = {0: Stem(id=0, channels=frozenset((ChannelName.PULSE2,)))}
        hierarchy = StemHierarchy(levels=((0,),), mode=HierarchyMode.STRICT)
        with pytest.raises(ValueError, match="configuration lacks"):
            _assign(synthetic_fragment, stems, hierarchy, channels, matcher, extractor, 1)

    def test_hierarchy_duplicating_a_stem_raises(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        stems = {0: Stem(id=0, channels=DEFAULT_CHANNELS)}
        hierarchy = StemHierarchy(levels=((0,), (0,)), mode=HierarchyMode.STRICT)
        with pytest.raises(ValueError, match="exactly once"):
            _assign(synthetic_fragment, stems, hierarchy, channels, matcher, extractor, 1)

    def test_hierarchy_leaving_a_stem_out_raises(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        stems = {
            0: Stem(id=0, channels=DEFAULT_CHANNELS),
            1: Stem(id=1, channels=frozenset((ChannelName.NOISE,))),
        }
        hierarchy = StemHierarchy(levels=((0,),), mode=HierarchyMode.STRICT)
        with pytest.raises(ValueError, match="exactly once"):
            _assign(synthetic_fragment, stems, hierarchy, channels, matcher, extractor, 1)

    def test_hierarchy_naming_an_unknown_stem_raises(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        stems = {0: Stem(id=0, channels=DEFAULT_CHANNELS)}
        hierarchy = StemHierarchy(levels=((0,), (5,)), mode=HierarchyMode.STRICT)
        with pytest.raises(ValueError, match="exactly once"):
            _assign(synthetic_fragment, stems, hierarchy, channels, matcher, extractor, 1)


class TestChannelCap:
    def test_strict_mode_respects_the_cap(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        stems = {0: Stem(id=0, channels=DEFAULT_CHANNELS)}
        hierarchy = StemHierarchy(levels=((0,),), mode=HierarchyMode.STRICT)

        for cap, expected_count in ((1, 1), (2, 2), (5, 3)):
            assignment = _assign(synthetic_fragment, stems, hierarchy, channels, matcher, extractor, cap)
            assert len(assignment.choices) == expected_count
            assert {choice.stem_id for choice in assignment.choices} == {0}

    def test_round_robin_mode_respects_the_cap(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        stems = {0: Stem(id=0, channels=DEFAULT_CHANNELS)}
        hierarchy = StemHierarchy(levels=((0,),), mode=HierarchyMode.ROUND_ROBIN)

        assignment = _assign(synthetic_fragment, stems, hierarchy, channels, matcher, extractor, 2)
        assert len(assignment.choices) == 2


class TestTieBreakDeterminism:
    def test_equal_cost_choices_go_to_the_first_stem_in_level_order(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        pulse_only = frozenset((ChannelName.PULSE1,))
        stems = {
            0: Stem(id=0, channels=pulse_only),
            1: Stem(id=1, channels=pulse_only),
        }

        first = _assign(
            synthetic_fragment,
            stems,
            StemHierarchy(levels=((0, 1),), mode=HierarchyMode.STRICT),
            channels,
            matcher,
            extractor,
            1,
        )
        assert [(choice.stem_id, choice.channel_name) for choice in first.choices] == [(0, ChannelName.PULSE1)]

        swapped = _assign(
            synthetic_fragment,
            stems,
            StemHierarchy(levels=((1, 0),), mode=HierarchyMode.STRICT),
            channels,
            matcher,
            extractor,
            1,
        )
        assert [(choice.stem_id, choice.channel_name) for choice in swapped.choices] == [(1, ChannelName.PULSE1)]

    def test_repeated_runs_give_identical_choices(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        stems = {
            0: Stem(id=0, channels=frozenset((ChannelName.PULSE1, ChannelName.TRIANGLE))),
            1: Stem(id=1, channels=frozenset((ChannelName.NOISE,))),
        }
        hierarchy = StemHierarchy(levels=((0,), (1,)), mode=HierarchyMode.STRICT)

        first = _assign(synthetic_fragment, stems, hierarchy, channels, matcher, extractor, 2)
        second = _assign(synthetic_fragment, stems, hierarchy, channels, matcher, extractor, 2)
        assert _choice_keys(first.choices) == _choice_keys(second.choices)


class TestHierarchyOrdering:
    def test_strict_mode_exhausts_the_first_level_before_the_next(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        stems = {
            0: Stem(id=0, channels=frozenset((ChannelName.PULSE1, ChannelName.TRIANGLE))),
            1: Stem(id=1, channels=frozenset((ChannelName.NOISE,))),
        }
        hierarchy = StemHierarchy(levels=((0,), (1,)), mode=HierarchyMode.STRICT)

        assignment = _assign(synthetic_fragment, stems, hierarchy, channels, matcher, extractor, 2)

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
        stems = {
            0: Stem(id=0, channels=frozenset((ChannelName.PULSE1, ChannelName.TRIANGLE))),
            1: Stem(id=1, channels=frozenset((ChannelName.NOISE,))),
        }
        hierarchy = StemHierarchy(levels=((0,), (1,)), mode=HierarchyMode.ROUND_ROBIN)

        assignment = _assign(synthetic_fragment, stems, hierarchy, channels, matcher, extractor, 2)

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
