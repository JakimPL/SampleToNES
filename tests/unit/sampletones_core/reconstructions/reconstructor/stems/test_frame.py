from typing import Dict, Final, List, Sequence, Tuple

import numpy as np
import pytest

from sampletones_core.constants.algorithm import SINGLE_STATE_LATTICE_WIDTH
from sampletones_core.constants.enums import (
    DEFAULT_CHANNELS,
    ChannelName,
    HierarchyMode,
    bending_channels,
)
from sampletones_core.fft import Fragment
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import GeneratorUnion
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.assignment.frame import assign_frame
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.models.choice import StemChoice
from sampletones_core.reconstructions.reconstructor.stems.models.frame_assignment import StemFrameAssignment

from .conftest import shared_frames

DEFAULT_CHANNELS: List[ChannelName] = [ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE]
LOUDER_STEM_SCALE: Final[float] = 4.0


def _config(
    entries: Dict[int, List[ChannelName]],
    levels: List[List[int]],
    mode: HierarchyMode,
    channel_cap: int,
) -> StemsConfig:
    return StemsConfig(
        entries=[
            StemEntry(id=stem_id, channels=channels, bends=bending_channels(channels))
            for stem_id, channels in entries.items()
        ],
        hierarchy=StemsHierarchy(levels=levels, mode=mode),
        channel_cap=channel_cap,
    )


def _assign(
    fragment: Fragment,
    stems_config: StemsConfig,
    channels: Dict[ChannelName, GeneratorUnion],
    matcher: FrameMatcher,
    extractor: FeatureExtractor,
    lattice_width: int = SINGLE_STATE_LATTICE_WIDTH,
) -> StemFrameAssignment:
    return assign_frame(
        shared_frames(fragment, stems_config),
        stems_config,
        channels,
        matcher,
        extractor,
        lattice_width,
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
        with pytest.raises(ValueError, match="the run was not built for"):
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


class TestSoundingStems:
    """A stem takes a channel where its own recording sounds, and stands aside where it does not."""

    def test_a_stem_sounding_nothing_leaves_the_channel_to_one_that_does(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        """A silent stem picking first passes, so the channel reaches the stem behind it.

        This is what keeps a recording quiet through a passage from sounding that passage on the
        channels it holds elsewhere.
        """
        stems_config = _config(
            {0: [ChannelName.PULSE1], 1: [ChannelName.PULSE1]},
            [[0], [1]],
            HierarchyMode.STRICT,
            1,
        )

        assignment = assign_frame(
            {0: synthetic_fragment * 0.0, 1: synthetic_fragment},
            stems_config,
            channels,
            matcher,
            extractor,
            SINGLE_STATE_LATTICE_WIDTH,
        )

        assert [choice.stem_id for choice in assignment.choices] == [1]
        assert assignment.resting == ()

    def test_a_frame_no_stem_sounds_in_rests_every_channel(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        """Every covered channel still answers the frame, each holding its null instruction."""
        stems_config = _config({0: DEFAULT_CHANNELS}, [[0]], HierarchyMode.STRICT, len(DEFAULT_CHANNELS))
        silent = synthetic_fragment * 0.0

        assignment = assign_frame(
            {0: silent},
            stems_config,
            channels,
            matcher,
            extractor,
            SINGLE_STATE_LATTICE_WIDTH,
        )

        assert assignment.choices == ()
        assert set(assignment.resting) == set(DEFAULT_CHANNELS)
        for rest in assignment.rests:
            assert not rest.column[0].instruction.on


class TestBidsWithinALevel:
    """Two stems sharing a level compete for a channel by what each still has to render."""

    def _pulse_cost(
        self,
        fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> float:
        pulse = channels[ChannelName.PULSE1]
        return matcher.score_candidates(fragment, {pulse.class_name(): pulse})[0].cost

    def test_the_louder_stem_takes_the_channel(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        """The louder recording wins the channel though the quieter one is the closer match.

        A cost is a fraction of its own recording's energy, so the quiet stem scores the better
        cost; weighting that cost by the energy behind it is what sends the channel where more
        sound is waiting. The winner follows the recordings, not the place a stem holds.
        """
        quiet = synthetic_fragment
        loud = synthetic_fragment * LOUDER_STEM_SCALE
        assert self._pulse_cost(quiet, channels, matcher) < self._pulse_cost(loud, channels, matcher)

        stems_config = _config(
            {0: [ChannelName.PULSE1], 1: [ChannelName.PULSE1]},
            [[0, 1]],
            HierarchyMode.STRICT,
            1,
        )

        for loud_stem_id in (0, 1):
            assignment = assign_frame(
                {loud_stem_id: loud, 1 - loud_stem_id: quiet},
                stems_config,
                channels,
                matcher,
                extractor,
                SINGLE_STATE_LATTICE_WIDTH,
            )

            assert [choice.stem_id for choice in assignment.choices] == [loud_stem_id]

    def test_a_level_of_its_own_takes_the_channel_first(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        """Levels pick in the order they are listed, so the first level takes the channel.

        Bids settle a level's own competition; precedence between levels stays the hierarchy's,
        which is what a reader arranges the levels to say.
        """
        stems_config = _config(
            {0: [ChannelName.PULSE1], 1: [ChannelName.PULSE1]},
            [[0], [1]],
            HierarchyMode.STRICT,
            1,
        )

        assignment = assign_frame(
            {0: synthetic_fragment, 1: synthetic_fragment * LOUDER_STEM_SCALE},
            stems_config,
            channels,
            matcher,
            extractor,
            SINGLE_STATE_LATTICE_WIDTH,
        )

        assert [choice.stem_id for choice in assignment.choices] == [0]


class TestColumns:
    """Every channel leaves the frame with the alternatives the decoder reads."""

    def test_a_narrow_lattice_answers_each_pick_with_itself(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        stems_config = _config({0: DEFAULT_CHANNELS}, [[0]], HierarchyMode.STRICT, len(DEFAULT_CHANNELS))

        assignment = _assign(synthetic_fragment, stems_config, channels, matcher, extractor)

        for choice in assignment.choices:
            assert len(choice.column) == SINGLE_STATE_LATTICE_WIDTH
            assert choice.column[0].instruction == choice.instruction

    def test_a_wide_lattice_holds_the_pick_among_its_alternatives(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        """A wider column reaches the winning channel's own candidates, the pick among them."""
        stems_config = _config({0: DEFAULT_CHANNELS}, [[0]], HierarchyMode.STRICT, len(DEFAULT_CHANNELS))
        width = matcher.top_k

        assignment = _assign(synthetic_fragment, stems_config, channels, matcher, extractor, width)

        for choice in assignment.choices:
            instructions = [candidate.instruction for candidate in choice.column]
            assert 0 < len(choice.column) <= width
            assert choice.instruction in instructions
            assert len(set(instructions)) == len(instructions)

    def test_a_wide_lattice_offers_one_channel_its_own_candidates(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        stems_config = _config({0: [ChannelName.PULSE1]}, [[0]], HierarchyMode.STRICT, 1)

        assignment = _assign(synthetic_fragment, stems_config, channels, matcher, extractor, matcher.top_k)

        column = assignment.by_channel[ChannelName.PULSE1].column
        pulse_class = channels[ChannelName.PULSE1].class_name()
        expected = matcher.score_candidates(synthetic_fragment, {pulse_class: channels[ChannelName.PULSE1]})
        assert [candidate.instruction for candidate in column] == [
            candidate.instruction for candidate in expected[: matcher.top_k]
        ]

    def test_a_resting_channel_holds_its_null_instruction_alone(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        """A rest is a column of one, so a channel no stem took still answers its frame."""
        stems_config = _config({0: DEFAULT_CHANNELS}, [[0]], HierarchyMode.STRICT, 1)

        assignment = _assign(synthetic_fragment, stems_config, channels, matcher, extractor, matcher.top_k)

        assert assignment.rests
        for rest in assignment.rests:
            assert len(rest.column) == SINGLE_STATE_LATTICE_WIDTH
            candidate = rest.column[0]
            assert candidate.instruction == channels[rest.channel_name].get_instruction_type().null_instruction()
            assert not np.any(np.asarray(candidate.approximation.audio))


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
