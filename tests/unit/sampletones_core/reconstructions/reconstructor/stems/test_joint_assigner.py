import itertools
from typing import Dict, Final, List, Optional, Set, Tuple

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import RESTING_FRAME_COST
from sampletones_core.constants.enums import (
    AssignmentMethod,
    ChannelName,
    HierarchyMode,
    bending_channels,
)
from sampletones_core.fft import Fragment
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import GeneratorUnion
from sampletones_core.instructions import InstructionUnion, PulseInstruction, TonalInstruction, TriangleInstruction
from sampletones_core.reconstructions.reconstructor.decoder.base import PooledCombination
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.assignment.assigners import PicksAssigner, frame_assigner
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.assigner import JointAssigner
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_core.reconstructions.reconstructor.stems.models.frame_assignment import StemFrameAssignment
from sampletones_core.reconstructions.reconstructor.stems.models.pool import StemPool

from ..conftest import rendered_fragment

LATTICE_WIDTH: Final[int] = 8
LEAD: Final[PulseInstruction] = PulseInstruction(on=True, pitch=64, volume=12, duty_cycle=2)
HARMONY: Final[PulseInstruction] = PulseInstruction(on=True, pitch=67, volume=8, duty_cycle=1)
BASS: Final[TriangleInstruction] = TriangleInstruction(on=True, pitch=48)
CHORD: Final[Dict[ChannelName, InstructionUnion]] = {
    ChannelName.PULSE1: LEAD,
    ChannelName.PULSE2: HARMONY,
    ChannelName.TRIANGLE: BASS,
}
EVERY_CHANNEL: Final[List[ChannelName]] = ChannelName.items()
NEXT_CHORD: Final[Dict[ChannelName, InstructionUnion]] = {
    ChannelName.PULSE1: PulseInstruction(on=True, pitch=62, volume=12, duty_cycle=2),
    ChannelName.PULSE2: PulseInstruction(on=True, pitch=65, volume=8, duty_cycle=1),
    ChannelName.TRIANGLE: TriangleInstruction(on=True, pitch=45),
}


def _one_stem(channels: List[ChannelName], channel_cap: int) -> StemsConfig:
    return StemsConfig(
        entries=[
            StemEntry(
                id=0,
                settings=StemSettings(channels=channels, bends=bending_channels(channels), channel_cap=channel_cap),
            )
        ],
        hierarchy=StemsHierarchy(levels=[[0]], mode=HierarchyMode.ROUND_ROBIN),
    )


def _assigner(
    stems: StemsConfig,
    channels: Dict[ChannelName, GeneratorUnion],
    matcher: FrameMatcher,
) -> JointAssigner:
    return JointAssigner(stems, channels, matcher, LATTICE_WIDTH)


def _heads(assignment: StemFrameAssignment) -> Dict[ChannelName, InstructionUnion]:
    return {choice.channel_name: choice.instruction for choice in assignment.choices}


def _notes(heads: Dict[ChannelName, InstructionUnion]) -> Set[Tuple[str, int]]:
    """The notes the heads sound, by kind of channel, the pulses one kind."""
    notes: Set[Tuple[str, int]] = set()
    for channel_name, instruction in heads.items():
        match instruction:
            case TonalInstruction(on=True):
                kind = "triangle" if channel_name == ChannelName.TRIANGLE else "pulse"
                notes.add((kind, instruction.pitch))
    return notes


@pytest.fixture(name="chord", scope="module")
def chord_fixture(config: Config, extractor: FeatureExtractor) -> Fragment:
    return rendered_fragment(config, extractor, CHORD)


class TestTheJointAssignment:
    def test_a_chord_s_notes_head_the_columns_on_their_own_kinds_of_channel(
        self,
        chord: Fragment,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        assigner = _assigner(
            StemsConfig.single_entry(StemSettings.covering(EVERY_CHANNEL)), all_channels, joint_matcher
        )

        heads = _heads(assigner.assign({0: chord}))

        assert _notes(heads) == {("pulse", 64), ("pulse", 67), ("triangle", 48)}

    def test_every_channel_held_offers_its_silence_within_the_width_the_decoder_reads(
        self,
        chord: Fragment,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        assigner = _assigner(
            StemsConfig.single_entry(StemSettings.covering(EVERY_CHANNEL)), all_channels, joint_matcher
        )

        assignment = assigner.assign({0: chord})

        assert {choice.channel_name for choice in assignment.choices} == set(EVERY_CHANNEL)
        for choice in assignment.choices:
            assert len(choice.column) <= LATTICE_WIDTH
            assert any(not candidate.instruction.on for candidate in choice.column)

    def test_a_silent_frame_rests_every_channel(
        self,
        config: Config,
        extractor: FeatureExtractor,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        assigner = _assigner(
            StemsConfig.single_entry(StemSettings.covering(EVERY_CHANNEL)), all_channels, joint_matcher
        )

        assignment = assigner.assign({0: rendered_fragment(config, extractor, {})})

        assert assignment.choices == ()
        assert {rest.channel_name for rest in assignment.rests} == set(EVERY_CHANNEL)

    def test_a_stem_counted_to_one_channel_holds_one_and_rests_the_rest(
        self,
        chord: Fragment,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        assigner = _assigner(
            _one_stem([ChannelName.PULSE1, ChannelName.PULSE2], channel_cap=1), all_channels, joint_matcher
        )

        assignment = assigner.assign({0: chord})

        assert len(assignment.choices) == 1
        assert len(assignment.rests) == 1

    def test_a_held_chord_keeps_each_pulse_note_on_its_channel(
        self,
        chord: Fragment,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        assigner = _assigner(
            StemsConfig.single_entry(StemSettings.covering(EVERY_CHANNEL)), all_channels, joint_matcher
        )

        first = _pulse_pitches(_heads(assigner.assign({0: chord})))
        second = _pulse_pitches(_heads(assigner.assign({0: chord})))

        assert first == second

    def test_stems_sharing_a_channel_are_refused(
        self,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        shared = StemsConfig(
            entries=[
                StemEntry(id=0, settings=StemSettings(channels=[ChannelName.PULSE1], bends=[], channel_cap=1)),
                StemEntry(id=1, settings=StemSettings(channels=[ChannelName.PULSE1], bends=[], channel_cap=1)),
            ],
            hierarchy=StemsHierarchy(levels=[[0, 1]], mode=HierarchyMode.ROUND_ROBIN),
        )

        with pytest.raises(ValueError, match="one stem"):
            _assigner(shared, all_channels, joint_matcher)


def _played(pool: StemPool, combination: PooledCombination) -> Dict[ChannelName, InstructionUnion]:
    return {name: candidate.instruction for name, candidate in zip(pool.channel_names, combination.candidates)}


def _pooled(pool: StemPool) -> List[Dict[ChannelName, InstructionUnion]]:
    return [_played(pool, combination) for combination in pool.combinations]


def _swapped(played: Dict[ChannelName, InstructionUnion]) -> Dict[ChannelName, InstructionUnion]:
    return {
        **played,
        ChannelName.PULSE1: played[ChannelName.PULSE2],
        ChannelName.PULSE2: played[ChannelName.PULSE1],
    }


@pytest.fixture(name="every_channel_assigner")
def every_channel_assigner_fixture(
    all_channels: Dict[ChannelName, GeneratorUnion], joint_matcher: FrameMatcher
) -> JointAssigner:
    return _assigner(StemsConfig.single_entry(StemSettings.covering(EVERY_CHANNEL)), all_channels, joint_matcher)


class TestTheJointPools:
    def test_a_sounding_frame_pools_the_choice_first(
        self, chord: Fragment, every_channel_assigner: JointAssigner
    ) -> None:
        assignment = every_channel_assigner.assign({0: chord})

        (pool,) = assignment.pools
        assert _played(pool, pool.combinations[0]) == _heads(assignment)

    def test_every_channel_of_a_combination_carries_the_combination_s_cost(
        self, chord: Fragment, every_channel_assigner: JointAssigner
    ) -> None:
        (pool,) = every_channel_assigner.assign({0: chord}).pools

        for combination in pool.combinations:
            assert {candidate.cost for candidate in combination.candidates} == {combination.cost}

    def test_every_combination_stands_in_both_orders_of_the_pulses(
        self, chord: Fragment, every_channel_assigner: JointAssigner
    ) -> None:
        (pool,) = every_channel_assigner.assign({0: chord}).pools
        pooled = _pooled(pool)

        for played in pooled:
            assert _swapped(played) in pooled

    def test_the_choice_is_pooled_with_every_set_of_its_sounding_channels_silenced(
        self, chord: Fragment, every_channel_assigner: JointAssigner, all_channels: Dict[ChannelName, GeneratorUnion]
    ) -> None:
        assignment = every_channel_assigner.assign({0: chord})
        (pool,) = assignment.pools
        heads = _heads(assignment)
        sounding = [channel_name for channel_name, instruction in heads.items() if instruction.on]
        pooled = _pooled(pool)

        for count in range(1, len(sounding) + 1):
            for silenced in itertools.combinations(sounding, count):
                quiet = {name: all_channels[name].get_instruction_type().null_instruction() for name in silenced}
                assert {**heads, **quiet} in pooled

    def test_the_choice_is_pooled_with_each_channel_moved_to_every_alternative_of_its_column(
        self, chord: Fragment, every_channel_assigner: JointAssigner
    ) -> None:
        """A path may take every move a decoder of one channel at a time could."""
        assignment = every_channel_assigner.assign({0: chord})
        (pool,) = assignment.pools
        heads = _heads(assignment)
        pooled = _pooled(pool)

        for choice in assignment.choices:
            for candidate in choice.column:
                assert {**heads, choice.channel_name: candidate.instruction} in pooled

    def test_the_previous_frame_s_choice_is_pooled(
        self, config: Config, extractor: FeatureExtractor, chord: Fragment, every_channel_assigner: JointAssigner
    ) -> None:
        before = _heads(every_channel_assigner.assign({0: chord}))

        (pool,) = every_channel_assigner.assign({0: rendered_fragment(config, extractor, NEXT_CHORD)}).pools

        assert before in _pooled(pool)

    def test_a_silent_frame_pools_every_channel_resting(
        self, config: Config, extractor: FeatureExtractor, every_channel_assigner: JointAssigner
    ) -> None:
        (pool,) = every_channel_assigner.assign({0: rendered_fragment(config, extractor, {})}).pools

        (resting,) = pool.combinations
        assert resting.cost == RESTING_FRAME_COST
        assert not any(candidate.instruction.on for candidate in resting.candidates)

    def test_a_stem_counted_to_one_channel_pools_combinations_sounding_one(
        self, chord: Fragment, all_channels: Dict[ChannelName, GeneratorUnion], joint_matcher: FrameMatcher
    ) -> None:
        assigner = _assigner(
            _one_stem([ChannelName.PULSE1, ChannelName.PULSE2], channel_cap=1), all_channels, joint_matcher
        )

        (pool,) = assigner.assign({0: chord}).pools

        assert all(
            sum(candidate.instruction.on for candidate in combination.candidates) <= 1
            for combination in pool.combinations
        )


class TestFrameAssigner:
    @pytest.mark.parametrize(
        "method, kind",
        [(AssignmentMethod.PICKS, PicksAssigner), (AssignmentMethod.JOINT, JointAssigner)],
        ids=["picks", "joint"],
    )
    def test_the_method_names_the_assigner(
        self,
        method: AssignmentMethod,
        kind: type,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        stems = StemsConfig.single_entry(StemSettings.covering(EVERY_CHANNEL))

        assert isinstance(frame_assigner(method, stems, all_channels, joint_matcher, LATTICE_WIDTH), kind)


def _pulse_pitches(heads: Dict[ChannelName, InstructionUnion]) -> Tuple[Optional[int], Optional[int]]:
    def pitch(channel_name: ChannelName) -> Optional[int]:
        match heads.get(channel_name):
            case PulseInstruction(on=True) as instruction:
                return instruction.pitch
            case _:
                return None

    return pitch(ChannelName.PULSE1), pitch(ChannelName.PULSE2)
