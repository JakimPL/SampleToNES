from typing import Dict, Final, List, Optional, Set, Tuple

import pytest

from sampletones_core.configs import Config
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
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.assignment.assigners import PicksAssigner, frame_assigner
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.assigner import JointAssigner
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_core.reconstructions.reconstructor.stems.models.frame_assignment import StemFrameAssignment

from .conftest import rendered_fragment

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
