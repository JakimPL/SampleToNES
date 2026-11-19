from typing import Dict, Final, List

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_tools.calibration.corpus.truth import sounding_pitches

A4: Final[int] = 69
OCTAVE: Final[float] = 2.0


@pytest.fixture(name="lines", scope="module")
def lines_fixture() -> Dict[ChannelName, List[InstructionUnion]]:
    return {
        ChannelName.PULSE1: [
            PulseInstruction(on=True, pitch=A4, volume=15, duty_cycle=2),
            PulseInstruction(on=False, pitch=A4, volume=0, duty_cycle=2),
            PulseInstruction(on=True, pitch=A4, volume=15, duty_cycle=2, detune=-8),
        ],
        ChannelName.TRIANGLE: [TriangleInstruction(on=True, pitch=A4)] * 3,
        ChannelName.NOISE: [NoiseInstruction(on=True, period=3, volume=9, short=False)] * 3,
    }


class TestSoundingPitches:
    def test_each_tonal_channel_has_a_line_and_the_noise_none(
        self,
        lines: Dict[ChannelName, List[InstructionUnion]],
    ) -> None:
        assert set(sounding_pitches(lines, Config())) == {ChannelName.PULSE1, ChannelName.TRIANGLE}

    def test_a_silent_frame_sounds_no_pitch(self, lines: Dict[ChannelName, List[InstructionUnion]]) -> None:
        assert sounding_pitches(lines, Config())[ChannelName.PULSE1][1] is None

    def test_the_triangle_sounds_an_octave_below_the_pulse_on_one_note(
        self,
        lines: Dict[ChannelName, List[InstructionUnion]],
    ) -> None:
        pitches = sounding_pitches(lines, Config())
        pulse, triangle = pitches[ChannelName.PULSE1][0], pitches[ChannelName.TRIANGLE][0]

        assert pulse is not None and triangle is not None
        assert pulse / triangle == pytest.approx(OCTAVE, rel=1e-2)

    def test_a_bend_moves_the_pitch_a_frame_sounds(self, lines: Dict[ChannelName, List[InstructionUnion]]) -> None:
        pulse = sounding_pitches(lines, Config())[ChannelName.PULSE1]
        plain, bent = pulse[0], pulse[2]

        assert plain is not None and bent is not None
        assert bent > plain
