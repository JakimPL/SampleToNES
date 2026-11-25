from dataclasses import dataclass
from typing import Dict, Final, List, Mapping, Optional, Sequence

import pytest

from sampletones_core.configs import Config
from sampletones_core.configs.generation import ChannelInertia
from sampletones_core.constants.enums import ChannelName
from sampletones_core.fft import Fragment, Window
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import GeneratorUnion
from sampletones_core.instructions import InstructionUnion, PulseInstruction
from sampletones_core.reconstructions.reconstructor.contribution import Contribution
from sampletones_core.reconstructions.reconstructor.decoder.transition import TransitionWeights
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.assigner import JointAssigner
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.neighbors import NeighborPass
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_core.reconstructions.reconstructor.stems.models.frame_assignment import StemFrameAssignment
from sampletones_core.reconstructions.reconstructor.window.profiles import frame_profiles
from tests.suite.base import BaseTestSuite

from .conftest import decoded_lines, played_lines

LATTICE_WIDTH: Final[int] = 8
FRAMES: Final[int] = 12
LONE_FRAMES: Final[int] = 1
LEAD: Final[PulseInstruction] = PulseInstruction(on=True, pitch=64, volume=12, duty_cycle=2)
JUMP: Final[PulseInstruction] = PulseInstruction(on=True, pitch=67, volume=12, duty_cycle=2)
SILENT: Final[PulseInstruction] = PulseInstruction.null_instruction()
WRONG_RUN: Final[range] = range(3, 9)
NO_INERTIA: Final[float] = 0.0
STRONG_INERTIA: Final[float] = 100.0

Lines = Mapping[ChannelName, Sequence[InstructionUnion]]


def _inertia(pulses: float) -> ChannelInertia:
    return ChannelInertia(pulse1=pulses, pulse2=pulses, triangle=NO_INERTIA, noise=NO_INERTIA)


def _lead(instructions: List[InstructionUnion]) -> Dict[ChannelName, List[InstructionUnion]]:
    return {ChannelName.PULSE1: instructions}


@dataclass(frozen=True)
class _Recording:
    """What a pass over a recording is built from: the configuration, its analysis and a stem over every channel."""

    config: Config
    window: Window
    extractor: FeatureExtractor
    channels: Dict[ChannelName, GeneratorUnion]
    matcher: FrameMatcher

    def assigner(self) -> JointAssigner:
        """A fresh assigner of one stem over every channel, its memory empty."""
        return JointAssigner(
            StemsConfig.single_entry(StemSettings.covering(ChannelName.items())),
            self.channels,
            self.matcher,
            LATTICE_WIDTH,
        )


class _Pass:
    """A recording played as ``played``, decoded as ``decoded``, and a neighbor pass over that decode."""

    def __init__(self, recording: _Recording, played: Lines, decoded: Lines, inertia: float) -> None:
        config = recording.config
        extractor = recording.extractor
        window = recording.window
        assigner = recording.assigner()
        frames = len(next(iter(played.values())))
        self.fragments: List[Fragment] = extractor.extract(played_lines(config, played, frames))
        bins = len(self.fragments[0].feature.values)
        silence = Contribution.silence(bins, config.library.frame_length)
        self.neighbor_pass = NeighborPass.over(
            assigner,
            decoded_lines(decoded, assigner.channels, silence, frames),
            frame_profiles(config, window, bins),
            TransitionWeights.of(config),
            _inertia(inertia),
        )

    def assigned(self, frame: int) -> StemFrameAssignment:
        return self.neighbor_pass.assign(frame, {0: self.fragments[frame]})

    def lead(self, frame: int) -> InstructionUnion:
        """What the pass's lines play on the first pulse at ``frame``."""
        return self.neighbor_pass.lines[ChannelName.PULSE1].instructions[frame]


def _head(assignment: StemFrameAssignment, channel_name: ChannelName) -> Optional[InstructionUnion]:
    choice = assignment.by_channel.get(channel_name)
    return None if choice is None else choice.instruction


def _pitch(instruction: Optional[InstructionUnion]) -> Optional[int]:
    """The pitch a pulse frame sounds, ``None`` for a silent one.

    A frame whose window reaches past the recording, or whose neighbors sound other than the decode says,
    reads its note's volume off the one played, so these cases compare pitches.
    """
    match instruction:
        case PulseInstruction(on=True):
            return instruction.pitch
        case _:
            return None


@pytest.fixture(name="recording", scope="module")
def recording_fixture(
    config: Config,
    window: Window,
    extractor: FeatureExtractor,
    all_channels: Dict[ChannelName, GeneratorUnion],
    joint_matcher: FrameMatcher,
) -> _Recording:
    return _Recording(config, window, extractor, all_channels, joint_matcher)


class TestTheNeighborPass(BaseTestSuite):
    """Frames are decided first to last, each settled into the lines before the next is decided."""

    def test_a_frame_s_choice_is_settled_into_the_lines_and_the_frames_after_keep_the_decode(
        self, recording: _Recording
    ) -> None:
        held = _Pass(recording, _lead([LEAD] * FRAMES), _lead([SILENT] * FRAMES), NO_INERTIA)

        head = _head(held.assigned(0), ChannelName.PULSE1)

        assert _pitch(head) == LEAD.pitch
        assert held.lead(0) == head
        assert [held.lead(frame) for frame in range(1, FRAMES)] == [SILENT] * (FRAMES - 1)

    def test_a_kept_frame_answers_to_the_choice_settled_before_it_so_a_wrong_run_is_put_right_in_turn(
        self, recording: _Recording
    ) -> None:
        """Each frame of a decoded hole ties between its settled note before and the hole after, so the sound decides."""
        decoded: List[InstructionUnion] = [SILENT if frame in WRONG_RUN else LEAD for frame in range(FRAMES)]
        held = _Pass(recording, _lead([LEAD] * FRAMES), _lead(decoded), STRONG_INERTIA)

        heads = [_head(held.assigned(frame), ChannelName.PULSE1) for frame in range(FRAMES)]

        assert heads == [LEAD] * FRAMES

    @pytest.mark.parametrize("first", [True, False], ids=["first-frame", "last-frame"])
    def test_a_frame_at_either_end_holds_to_its_one_neighbor(self, first: bool, recording: _Recording) -> None:
        end = 0 if first else FRAMES - 1
        played: List[InstructionUnion] = [JUMP if frame == end else LEAD for frame in range(FRAMES)]
        free = _Pass(recording, _lead(played), _lead([LEAD] * FRAMES), NO_INERTIA)
        kept = _Pass(recording, _lead(played), _lead([LEAD] * FRAMES), STRONG_INERTIA)

        assert _pitch(_head(free.assigned(end), ChannelName.PULSE1)) == JUMP.pitch
        assert _pitch(_head(kept.assigned(end), ChannelName.PULSE1)) == LEAD.pitch

    def test_a_recording_of_one_frame_follows_its_sound_whatever_the_inertia(self, recording: _Recording) -> None:
        lone = _Pass(recording, _lead([LEAD]), _lead([SILENT]), STRONG_INERTIA)

        assert len(lone.fragments) == LONE_FRAMES
        assert _pitch(_head(lone.assigned(0), ChannelName.PULSE1)) == LEAD.pitch
