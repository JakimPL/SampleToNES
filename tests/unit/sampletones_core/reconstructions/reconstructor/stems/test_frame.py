from dataclasses import dataclass, field
from typing import Dict, Final, List, Sequence, Set, Tuple

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import (
    ALL_STEMS_CHANNEL_CAP,
    MAX_DRIVE,
    SINGLE_STATE_LATTICE_WIDTH,
    UNIT_DRIVE,
)
from sampletones_core.constants.enums import (
    DEFAULT_CHANNELS,
    ChannelName,
    GeneratorClassName,
    HierarchyMode,
    bending_channels,
)
from sampletones_core.fft import Fragment, Window
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import GeneratorUnion
from sampletones_core.library import InstructionLibraryData
from sampletones_core.reconstructions.reconstructor.matching import Column, FrameMatcher, column_of
from sampletones_core.reconstructions.reconstructor.mix import FrameMix
from sampletones_core.reconstructions.reconstructor.stems.assignment.frame import assign_frame
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_core.reconstructions.reconstructor.stems.models.choice import StemChoice
from sampletones_core.reconstructions.reconstructor.stems.models.frame_assignment import StemFrameAssignment
from sampletones_core.structures.histogram import Histogram
from tests.suite.fragments import amplified

from .conftest import audible_instruction_of, rendered_fragment, shared_frames

DEFAULT_CHANNELS: List[ChannelName] = [ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE]
LOUDER_STEM_SCALE: Final[float] = 4.0
LOUD_DRIVE: Final[float] = 2.0
SWEPT_DRIVES: Final[Tuple[float, ...]] = (UNIT_DRIVE, LOUD_DRIVE, MAX_DRIVE)


def _config(
    entries: Dict[int, List[ChannelName]],
    levels: List[List[int]],
    mode: HierarchyMode,
    channel_cap: int,
) -> StemsConfig:
    return StemsConfig(
        entries=[
            StemEntry(
                id=stem_id,
                settings=StemSettings(channels=channels, bends=bending_channels(channels), channel_cap=channel_cap),
            )
            for stem_id, channels in entries.items()
        ],
        hierarchy=StemsHierarchy(levels=levels, mode=mode),
    )


def _assign(
    fragment: Fragment,
    stems_config: StemsConfig,
    channels: Dict[ChannelName, GeneratorUnion],
    matcher: FrameMatcher,
    lattice_width: int = SINGLE_STATE_LATTICE_WIDTH,
) -> StemFrameAssignment:
    return assign_frame(
        shared_frames(fragment, stems_config),
        stems_config,
        channels,
        matcher,
        lattice_width,
    )


class TestAssignFrameValidation:
    def test_channel_outside_enabled_channels_raises(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        stems_config = _config({0: [ChannelName.PULSE2]}, [[0]], HierarchyMode.STRICT, 1)
        with pytest.raises(ValueError, match="the run was not built for"):
            _assign(synthetic_fragment, stems_config, channels, matcher)


class TestFrameCompleteness:
    """Every covered channel leaves the frame either picked or resting, never neither."""

    def test_a_capped_frame_rests_the_channels_no_stem_took(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        stems_config = _config({0: DEFAULT_CHANNELS}, [[0]], HierarchyMode.STRICT, 1)

        assignment = _assign(synthetic_fragment, stems_config, channels, matcher)

        assert len(assignment.choices) == 1
        assert set(assignment.by_channel) | set(assignment.resting) == stems_config.covered_channels
        assert set(assignment.by_channel).isdisjoint(assignment.resting)

    def test_a_full_frame_rests_nothing(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        stems_config = _config({0: DEFAULT_CHANNELS}, [[0]], HierarchyMode.STRICT, len(DEFAULT_CHANNELS))

        assignment = _assign(synthetic_fragment, stems_config, channels, matcher)

        assert assignment.resting == ()
        assert set(assignment.by_channel) == stems_config.covered_channels

    def test_a_channel_no_stem_may_occupy_stays_out_of_the_frame(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        stems_config = _config({0: [ChannelName.PULSE1]}, [[0]], HierarchyMode.STRICT, 1)

        assignment = _assign(synthetic_fragment, stems_config, channels, matcher)

        assert set(assignment.by_channel) == {ChannelName.PULSE1}
        assert assignment.resting == ()


class TestSoundingStems:
    """A stem takes a channel where its own recording sounds, and stands aside where it does not."""

    def test_a_stem_sounding_nothing_leaves_the_channel_to_one_that_does(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
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
            {0: _silent(synthetic_fragment), 1: synthetic_fragment},
            stems_config,
            channels,
            matcher,
            SINGLE_STATE_LATTICE_WIDTH,
        )

        assert [choice.stem_id for choice in assignment.choices] == [1]
        assert assignment.resting == ()

    def test_a_frame_no_stem_sounds_in_rests_every_channel(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        """Every covered channel still answers the frame, each holding its null instruction."""
        stems_config = _config({0: DEFAULT_CHANNELS}, [[0]], HierarchyMode.STRICT, len(DEFAULT_CHANNELS))
        silent = _silent(synthetic_fragment)

        assignment = assign_frame(
            {0: silent},
            stems_config,
            channels,
            matcher,
            SINGLE_STATE_LATTICE_WIDTH,
        )

        assert assignment.choices == ()
        assert set(assignment.resting) == set(DEFAULT_CHANNELS)
        for rest in assignment.rests:
            assert not rest.column[0].instruction.on


class TestImprovementsWithinALevel:
    """Two stems sharing a level compete for a channel by how much of their sound it covers."""

    def test_the_louder_stem_takes_the_channel(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        extractor: FeatureExtractor,
    ) -> None:
        """The louder recording wins the channel where both are covered alike.

        A cost is a fraction of its own recording's energy, so the two stems lower their costs by
        the same fraction; weighting that lowering by the energy behind it is what sends the channel
        where more sound is waiting. The winner follows the recordings, not the place a stem holds.
        """
        quiet = synthetic_fragment
        loud = amplified(extractor, synthetic_fragment, LOUDER_STEM_SCALE)

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

        Improvements settle a level's own competition; precedence between levels stays the hierarchy's,
        which is what a reader arranges the levels to say.
        """
        stems_config = _config(
            {0: [ChannelName.PULSE1], 1: [ChannelName.PULSE1]},
            [[0], [1]],
            HierarchyMode.STRICT,
            1,
        )

        assignment = assign_frame(
            {0: synthetic_fragment, 1: amplified(extractor, synthetic_fragment, LOUDER_STEM_SCALE)},
            stems_config,
            channels,
            matcher,
            SINGLE_STATE_LATTICE_WIDTH,
        )

        assert [choice.stem_id for choice in assignment.choices] == [0]


class TestDrivesLeaveTheCompetitionStanding:
    """A drive settles what a channel plays and leaves the stems competing where they stood.

    This is the contract ``docs/concepts/stems.md`` states of a drive: raising one lifts the part of the mix its own channel carries, while the stems beside it hold
    the channels they held.
    """

    @staticmethod
    def _stems_config(driven_stem_id: int, drive: float) -> StemsConfig:
        """Two stems on one level reaching for the first pulse, one of them pushed to ``drive``."""
        held = [ChannelName.PULSE1]
        return StemsConfig(
            entries=[
                StemEntry(
                    id=stem_id,
                    settings=StemSettings(
                        channels=held,
                        bends=bending_channels(held),
                        drives={ChannelName.PULSE1: drive if stem_id == driven_stem_id else UNIT_DRIVE},
                        channel_cap=1,
                    ),
                )
                for stem_id in (0, 1)
            ],
            hierarchy=StemsHierarchy(levels=[[0, 1]], mode=HierarchyMode.STRICT),
        )

    def _winner(
        self,
        fragments: Dict[int, Fragment],
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        driven_stem_id: int,
        drive: float,
    ) -> int:
        """The stem the first pulse reaches with ``driven_stem_id`` pushed to ``drive``."""
        assignment = assign_frame(
            fragments,
            self._stems_config(driven_stem_id, drive),
            channels,
            matcher,
            SINGLE_STATE_LATTICE_WIDTH,
        )
        return assignment.by_channel[ChannelName.PULSE1].stem_id

    @pytest.mark.parametrize("driven_stem_id", (0, 1))
    def test_the_channel_holds_its_stem_at_every_drive(
        self,
        driven_stem_id: int,
        audible_fragments: List[Fragment],
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        """Two recordings reaching for one channel keep it where it stood, whichever is pushed.

        The stems are ranked on the channel read at unit drive, so the winner follows the
        recordings alone and a reader raising a drive hears that stem louder where it stood. The
        sweep stands at and above the level the library is calibrated to, the range this
        library's rows answer.
        """
        assert len(audible_fragments) >= 2
        fragments = {0: audible_fragments[0], 1: audible_fragments[-1]}
        standing = self._winner(fragments, channels, matcher, driven_stem_id, UNIT_DRIVE)

        winners = {drive: self._winner(fragments, channels, matcher, driven_stem_id, drive) for drive in SWEPT_DRIVES}

        assert winners == {drive: standing for drive in SWEPT_DRIVES}


class TestColumns:
    """Every channel leaves the frame with the alternatives the decoder reads."""

    def test_a_narrow_lattice_answers_each_pick_with_itself(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        stems_config = _config({0: DEFAULT_CHANNELS}, [[0]], HierarchyMode.STRICT, len(DEFAULT_CHANNELS))

        assignment = _assign(synthetic_fragment, stems_config, channels, matcher)

        for choice in assignment.choices:
            assert len(choice.column) == SINGLE_STATE_LATTICE_WIDTH
            assert choice.column[0].instruction == choice.instruction

    def test_a_wide_lattice_holds_the_pick_among_its_alternatives(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        """A wider column reaches the winning channel's own candidates, the pick among them."""
        stems_config = _config({0: DEFAULT_CHANNELS}, [[0]], HierarchyMode.STRICT, len(DEFAULT_CHANNELS))
        width = matcher.top_k

        assignment = _assign(synthetic_fragment, stems_config, channels, matcher, width)

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
    ) -> None:
        stems_config = _config({0: [ChannelName.PULSE1]}, [[0]], HierarchyMode.STRICT, 1)

        assignment = _assign(synthetic_fragment, stems_config, channels, matcher, matcher.top_k)

        column = assignment.by_channel[ChannelName.PULSE1].column
        expected = matcher.score_column(
            synthetic_fragment,
            channels[ChannelName.PULSE1],
            FrameMix.empty(synthetic_fragment),
            drive=UNIT_DRIVE,
        )
        assert [candidate.instruction for candidate in column] == [
            candidate.instruction for candidate in column_of(expected, matcher.top_k)
        ]

    def test_a_resting_channel_holds_its_null_instruction_alone(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        """A rest is a column of one, so a channel no stem took still answers its frame."""
        stems_config = _config({0: DEFAULT_CHANNELS}, [[0]], HierarchyMode.STRICT, 1)

        assignment = _assign(synthetic_fragment, stems_config, channels, matcher, matcher.top_k)

        assert assignment.rests
        for rest in assignment.rests:
            assert len(rest.column) == SINGLE_STATE_LATTICE_WIDTH
            candidate = rest.column[0]
            assert candidate.instruction == channels[rest.channel_name].get_instruction_type().null_instruction()
            assert not np.any(candidate.contribution.expectation)


class TestChannelCap:
    def test_strict_mode_respects_the_cap(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        for cap, expected_count in ((1, 1), (2, 2), (ALL_STEMS_CHANNEL_CAP, 3)):
            stems_config = _config({0: DEFAULT_CHANNELS}, [[0]], HierarchyMode.STRICT, cap)
            assignment = _assign(synthetic_fragment, stems_config, channels, matcher)
            assert len(assignment.choices) == expected_count
            assert {choice.stem_id for choice in assignment.choices} == {0}
            assert len(assignment.resting) == len(DEFAULT_CHANNELS) - expected_count

    def test_no_more_channels_sound_than_the_cap_allows(
        self,
        config: Config,
        extractor: FeatureExtractor,
        library_data: InstructionLibraryData,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        """A frame every channel could answer sounds as many channels as the cap allows at most."""
        fragment = _every_kind(config, extractor, library_data, channels)
        for cap in (1, 2):
            stems_config = _config({0: DEFAULT_CHANNELS}, [[0]], HierarchyMode.STRICT, cap)
            assignment = _assign(fragment, stems_config, channels, matcher, matcher.top_k)
            assert sum(choice.sounding for choice in assignment.choices) <= cap

    def test_round_robin_mode_respects_the_cap(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        stems_config = _config({0: DEFAULT_CHANNELS}, [[0]], HierarchyMode.ROUND_ROBIN, 2)

        assignment = _assign(synthetic_fragment, stems_config, channels, matcher)

        assert len(assignment.choices) == 2
        assert len(assignment.resting) == 1


class TestPerStemCount:
    """Each stem holds at most the count its own settings allow, whatever the stems beside it allow."""

    def test_each_stem_holds_to_its_own_count(
        self,
        config: Config,
        extractor: FeatureExtractor,
        library_data: InstructionLibraryData,
        all_channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        fragment = _every_kind(config, extractor, library_data, all_channels)
        stems_config = StemsConfig(
            entries=[
                StemEntry(
                    id=0,
                    settings=StemSettings(channels=[ChannelName.PULSE1, ChannelName.TRIANGLE], bends=[], channel_cap=1),
                ),
                StemEntry(
                    id=1,
                    settings=StemSettings(channels=[ChannelName.PULSE2, ChannelName.NOISE], bends=[], channel_cap=2),
                ),
            ],
            hierarchy=StemsHierarchy(levels=[[0, 1]], mode=HierarchyMode.STRICT),
        )

        assignment = assign_frame(
            {0: fragment, 1: fragment},
            stems_config,
            all_channels,
            matcher,
            SINGLE_STATE_LATTICE_WIDTH,
        )

        held = {stem_id: [choice for choice in assignment.choices if choice.stem_id == stem_id] for stem_id in (0, 1)}
        assert len(held[0]) == 1
        assert len(held[1]) == 2
        assert set(assignment.by_channel) | set(assignment.resting) == stems_config.covered_channels

    def test_a_count_above_the_channels_held_sounds_the_channels_held(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        stems_config = _config({0: [ChannelName.PULSE1]}, [[0]], HierarchyMode.STRICT, ALL_STEMS_CHANNEL_CAP)

        assignment = _assign(synthetic_fragment, stems_config, channels, matcher)

        assert [choice.channel_name for choice in assignment.choices] == [ChannelName.PULSE1]
        assert assignment.resting == ()


@dataclass(frozen=True)
class _CountingMatcher(FrameMatcher):
    """A matcher recording every column it was asked for, so a case reads what was scored apart."""

    requests: List[Tuple[GeneratorClassName, float]] = field(default_factory=list)

    def score_column(
        self,
        target: Fragment,
        generator: GeneratorUnion,
        mix: FrameMix,
        *,
        drive: float,
    ) -> Column:
        self.requests.append((generator.class_name(), drive))
        return super().score_column(target, generator, mix, drive=drive)


class TestDrivenColumns:
    """A stem's channels are scored at the drives its settings give them."""

    def test_channels_of_one_kind_driven_alike_are_scored_at_that_drive(
        self,
        config: Config,
        extractor: FeatureExtractor,
        library_data: InstructionLibraryData,
        all_channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        counting = _counting(matcher)

        _assign_pulses(
            _every_kind(config, extractor, library_data, all_channels),
            {ChannelName.PULSE1: UNIT_DRIVE, ChannelName.PULSE2: UNIT_DRIVE},
            all_channels,
            counting,
        )

        assert _pulse_drives(counting) == {UNIT_DRIVE}

    def test_channels_of_one_kind_driven_apart_are_scored_apart(
        self,
        config: Config,
        extractor: FeatureExtractor,
        library_data: InstructionLibraryData,
        all_channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        counting = _counting(matcher)

        _assign_pulses(
            _every_kind(config, extractor, library_data, all_channels),
            {ChannelName.PULSE1: UNIT_DRIVE, ChannelName.PULSE2: LOUD_DRIVE},
            all_channels,
            counting,
        )

        assert _pulse_drives(counting) == {UNIT_DRIVE, LOUD_DRIVE}


class TestTieBreakDeterminism:
    def test_equal_cost_choices_go_to_the_first_stem_in_level_order(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        entries = {0: [ChannelName.PULSE1], 1: [ChannelName.PULSE1]}

        first = _assign(
            synthetic_fragment,
            _config(entries, [[0, 1]], HierarchyMode.STRICT, 1),
            channels,
            matcher,
        )
        assert [(choice.stem_id, choice.channel_name) for choice in first.choices] == [(0, ChannelName.PULSE1)]

        swapped = _assign(
            synthetic_fragment,
            _config(entries, [[1, 0]], HierarchyMode.STRICT, 1),
            channels,
            matcher,
        )
        assert [(choice.stem_id, choice.channel_name) for choice in swapped.choices] == [(1, ChannelName.PULSE1)]

    def test_repeated_runs_give_identical_choices(
        self,
        synthetic_fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        stems_config = _config(
            {0: [ChannelName.PULSE1, ChannelName.TRIANGLE], 1: [ChannelName.NOISE]},
            [[0], [1]],
            HierarchyMode.STRICT,
            2,
        )

        first = _assign(synthetic_fragment, stems_config, channels, matcher)
        second = _assign(synthetic_fragment, stems_config, channels, matcher)

        assert _choice_keys(first.choices) == _choice_keys(second.choices)
        assert first.resting == second.resting


class TestHierarchyOrdering:
    """Levels take their channels in the hierarchy's mode, each stem answering its own sound."""

    def _frames(
        self,
        config: Config,
        extractor: FeatureExtractor,
        library_data: InstructionLibraryData,
        channels: Dict[ChannelName, GeneratorUnion],
    ) -> Dict[int, Fragment]:
        pulse_and_triangle = {
            channel_name: audible_instruction_of(library_data, channels[channel_name])
            for channel_name in (ChannelName.PULSE1, ChannelName.TRIANGLE)
        }
        pulse = {ChannelName.PULSE1: audible_instruction_of(library_data, channels[ChannelName.PULSE1])}
        return {
            0: rendered_fragment(config, extractor, pulse_and_triangle),
            1: rendered_fragment(config, extractor, pulse),
        }

    def _stems(self, mode: HierarchyMode) -> StemsConfig:
        return _config(
            {0: [ChannelName.PULSE1, ChannelName.TRIANGLE], 1: [ChannelName.PULSE2]},
            [[0], [1]],
            mode,
            2,
        )

    def test_strict_mode_exhausts_the_first_level_before_the_next(
        self,
        config: Config,
        extractor: FeatureExtractor,
        library_data: InstructionLibraryData,
        all_channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        assignment = assign_frame(
            self._frames(config, extractor, library_data, all_channels),
            self._stems(HierarchyMode.STRICT),
            all_channels,
            matcher,
            SINGLE_STATE_LATTICE_WIDTH,
        )

        assert [choice.stem_id for choice in assignment.choices] == [0, 0, 1]
        assert {choice.channel_name for choice in assignment.choices[:2]} == {
            ChannelName.PULSE1,
            ChannelName.TRIANGLE,
        }
        assert assignment.choices[2].channel_name == ChannelName.PULSE2
        assert all(choice.sounding for choice in assignment.choices)

    def test_round_robin_mode_alternates_levels_each_round(
        self,
        config: Config,
        extractor: FeatureExtractor,
        library_data: InstructionLibraryData,
        all_channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        assignment = assign_frame(
            self._frames(config, extractor, library_data, all_channels),
            self._stems(HierarchyMode.ROUND_ROBIN),
            all_channels,
            matcher,
            SINGLE_STATE_LATTICE_WIDTH,
        )

        assert [choice.stem_id for choice in assignment.choices] == [0, 1, 0]
        assert assignment.choices[1].channel_name == ChannelName.PULSE2
        assert {assignment.choices[0].channel_name, assignment.choices[2].channel_name} == {
            ChannelName.PULSE1,
            ChannelName.TRIANGLE,
        }


class TestPicksThatStop:
    """A channel sounds where it lowers the frame's cost, and holds its silence elsewhere."""

    def test_a_frame_one_channel_renders_whole_sounds_that_channel_alone(
        self,
        config: Config,
        window: Window,
        library_data: InstructionLibraryData,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        """The triangle's own frame costs nothing with the triangle sounding, so no other channel lowers it."""
        stems_config = _config({0: DEFAULT_CHANNELS}, [[0]], HierarchyMode.STRICT, len(DEFAULT_CHANNELS))

        assignment = _assign(
            self._triangle_frame(config, window, library_data, channels), stems_config, channels, matcher, matcher.top_k
        )

        assert [choice.channel_name for choice in assignment.choices if choice.sounding] == [ChannelName.TRIANGLE]
        assert assignment.resting == ()

    def test_a_declined_channel_keeps_its_alternatives_headed_by_silence(
        self,
        config: Config,
        window: Window,
        library_data: InstructionLibraryData,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        stems_config = _config({0: DEFAULT_CHANNELS}, [[0]], HierarchyMode.STRICT, len(DEFAULT_CHANNELS))

        assignment = _assign(
            self._triangle_frame(config, window, library_data, channels), stems_config, channels, matcher, matcher.top_k
        )

        declined = [choice for choice in assignment.choices if not choice.sounding]
        assert declined
        for choice in declined:
            assert len(choice.column) > 1
            assert any(candidate.instruction.on for candidate in choice.column)

    @staticmethod
    def _triangle_frame(
        config: Config,
        window: Window,
        library_data: InstructionLibraryData,
        channels: Dict[ChannelName, GeneratorUnion],
    ) -> Fragment:
        triangle = audible_instruction_of(library_data, channels[ChannelName.TRIANGLE])
        return library_data[triangle].get_fragment(0, config, window)


def _counting(matcher: FrameMatcher) -> _CountingMatcher:
    """The same matching machinery, keeping a record of the columns it scores."""
    return _CountingMatcher(
        config=matcher.config,
        candidate_provider=matcher.candidate_provider,
        scorer=matcher.scorer,
        phase_aligner=matcher.phase_aligner,
    )


def _assign_pulses(
    fragment: Fragment,
    drives: Dict[ChannelName, float],
    channels: Dict[ChannelName, GeneratorUnion],
    matcher: FrameMatcher,
) -> StemFrameAssignment:
    """One frame of a stem holding both pulses at the drives it gives them."""
    stems_config = StemsConfig(
        entries=[
            StemEntry(
                id=0,
                settings=StemSettings(
                    channels=list(drives),
                    bends=[],
                    drives=drives,
                    channel_cap=len(drives),
                ),
            )
        ],
        hierarchy=StemsHierarchy(levels=[[0]], mode=HierarchyMode.STRICT),
    )
    return assign_frame(
        shared_frames(fragment, stems_config),
        stems_config,
        channels,
        matcher,
        SINGLE_STATE_LATTICE_WIDTH,
    )


def _pulse_drives(matcher: _CountingMatcher) -> Set[float]:
    """The drives the pulse class was scored at over the whole frame."""
    return {drive for class_name, drive in matcher.requests if class_name == GeneratorClassName.PULSE_GENERATOR}


def _silent(fragment: Fragment) -> Fragment:
    """The same frame holding no sound."""
    return Fragment(
        audio=np.zeros_like(np.asarray(fragment.audio)),
        feature=Histogram(edges=fragment.feature.edges, values=np.zeros_like(np.asarray(fragment.feature.values))),
        windowed_audio=np.zeros_like(np.asarray(fragment.windowed_audio)),
        config=fragment.config,
    )


def _every_kind(
    config: Config,
    extractor: FeatureExtractor,
    library_data: InstructionLibraryData,
    channels: Dict[ChannelName, GeneratorUnion],
) -> Fragment:
    return rendered_fragment(
        config,
        extractor,
        {channel_name: audible_instruction_of(library_data, generator) for channel_name, generator in channels.items()},
    )


def _choice_keys(choices: Sequence[StemChoice]) -> Tuple[Tuple[int, ChannelName], ...]:
    return tuple((choice.stem_id, choice.channel_name) for choice in choices)
