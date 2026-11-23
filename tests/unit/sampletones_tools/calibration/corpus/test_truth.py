from dataclasses import dataclass
from functools import partial
from typing import Dict, Final, List

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_tools.calibration.corpus.truth import (
    audible,
    frame_middles,
    frames_reached,
    pitch_line,
    sounding_pitches,
    steady,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

A4: Final[int] = 69
OCTAVE: Final[float] = 2.0
FRAME_RATE: Final[int] = 60
SAMPLE_RATE: Final[int] = 22050
FREQUENCY: Final[float] = 440.0
AUDIBLE_FLOOR: Final[float] = 0.25


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


class TestFramesReached(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        samples: int

    test_cases = (
        TestCase(samples=SAMPLE_RATE, expected=FRAME_RATE, label="a whole number of frames"),
        TestCase(samples=SAMPLE_RATE + 1, expected=FRAME_RATE + 1, label="a frame reached into by one sample"),
        TestCase(samples=SAMPLE_RATE // FRAME_RATE - 1, expected=1, label="less than one frame"),
        TestCase(samples=SAMPLE_RATE // FRAME_RATE, expected=1, label="one frame exactly"),
        TestCase(samples=round(0.75 * SAMPLE_RATE), expected=46, label="three quarters of a second rounded up"),
        TestCase(samples=0, expected=0, label="no samples at all"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_a_frame_reached_into_partly_counts(self, test_case: TestCase) -> None:
        assert frames_reached(test_case.samples, SAMPLE_RATE, FRAME_RATE) == test_case.expected


def _fading(times: np.ndarray) -> np.ndarray:
    return 1.0 - times


class TestPitchLine:
    def test_a_steady_sound_holds_its_frequency_in_every_frame(self) -> None:
        line = pitch_line(partial(steady, FREQUENCY), partial(audible, _fading, 0.0), FRAME_RATE, FRAME_RATE)

        assert line == (FREQUENCY,) * FRAME_RATE

    def test_a_frame_is_silent_where_the_sound_falls_below_the_audible_floor_at_its_middle(self) -> None:
        sounding_at = partial(audible, _fading, AUDIBLE_FLOOR)
        line = pitch_line(partial(steady, FREQUENCY), sounding_at, FRAME_RATE, FRAME_RATE)
        heard = [(frame + 0.5) / FRAME_RATE <= 1.0 - AUDIBLE_FLOOR for frame in range(FRAME_RATE)]

        assert any(heard) and not all(heard)
        assert line == tuple(FREQUENCY if sounding else None for sounding in heard)

    def test_no_frames_make_an_empty_line(self) -> None:
        assert pitch_line(partial(steady, FREQUENCY), partial(audible, _fading, AUDIBLE_FLOOR), 0, FRAME_RATE) == ()


class TestAudible(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        level: float

    test_cases = (
        TestCase(level=1.0, expected=True, label="at full level"),
        TestCase(level=AUDIBLE_FLOOR, expected=True, label="at the floor"),
        TestCase(level=AUDIBLE_FLOOR / 2, expected=False, label="below the floor"),
        TestCase(level=0.0, expected=False, label="silent"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_a_sound_counts_as_sounding_at_or_above_the_floor(self, test_case: TestCase) -> None:
        level = partial(np.full_like, fill_value=test_case.level)

        assert bool(audible(level, AUDIBLE_FLOOR, np.zeros(1))[0]) is test_case.expected
