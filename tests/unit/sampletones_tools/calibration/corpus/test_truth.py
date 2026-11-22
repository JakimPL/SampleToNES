from dataclasses import dataclass
from typing import Dict, Final, List

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_tools.calibration.corpus.truth import frame_middles, frames_covering, sounding_pitches
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

A4: Final[int] = 69
OCTAVE: Final[float] = 2.0
FRAME_RATE: Final[int] = 60


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

    def test_no_frames_leave_no_lines(self) -> None:
        assert not sounding_pitches({}, Config())

    def test_a_channel_of_no_frames_has_an_empty_line(self) -> None:
        assert sounding_pitches({ChannelName.PULSE2: []}, Config()) == {ChannelName.PULSE2: ()}


class TestFrameMiddles(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        first: int
        count: int

    test_cases = (
        TestCase(first=0, count=1, label="the first frame alone"),
        TestCase(first=0, count=FRAME_RATE, label="a second from the start"),
        TestCase(first=17, count=5, label="a window further on"),
        TestCase(first=3, count=0, label="no frames"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_each_frame_is_read_halfway_between_its_edges(self, test_case: TestCase) -> None:
        middles = frame_middles(test_case.first, test_case.count, FRAME_RATE)
        starts = np.arange(test_case.first, test_case.first + test_case.count) / FRAME_RATE

        assert middles.shape == (test_case.count,)
        np.testing.assert_allclose(middles - starts, 0.5 / FRAME_RATE)


class TestFramesCovering(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        seconds: float

    test_cases = (
        TestCase(seconds=1.0, expected=FRAME_RATE, label="a whole number of frames"),
        TestCase(seconds=1.0 + 0.1 / FRAME_RATE, expected=FRAME_RATE + 1, label="a frame reached into partly"),
        TestCase(seconds=0.5 / FRAME_RATE, expected=1, label="less than one frame"),
        TestCase(seconds=0.0, expected=0, label="no time at all"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_a_frame_reached_into_partly_counts(self, test_case: TestCase) -> None:
        assert frames_covering(test_case.seconds, FRAME_RATE) == test_case.expected
