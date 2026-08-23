from dataclasses import dataclass
from typing import Optional, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.instructions import InstructionUnion, PulseInstruction
from sampletones_core.performance import ChannelPerformance, VoiceReading, sound_tick
from sampletones_core.project.voices.loop import WHOLE_LOOP_POINT
from sampletones_core.project.voices.sample import Sample
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.performance import make_pulse_reconstruction

ENVELOPE_TICKS: int = 3
SOUNDING_PITCH: int = 60
TAIL_LOOP_POINT: int = ENVELOPE_TICKS - 1


def _reading(loop_point: Optional[int]) -> VoiceReading:
    """A pulse voice over a three-tick envelope, read the way a channel reads it."""
    voice = Sample(
        name="lead",
        reconstruction=make_pulse_reconstruction(pitch=SOUNDING_PITCH, count=ENVELOPE_TICKS),
        loop_point=loop_point,
    )
    reading = VoiceReading.read(voice, ChannelName.PULSE1)
    assert reading is not None
    return reading


class TestSoundTick(BaseTestSuite):
    """Which of a voice's instructions a channel reaches, and where it runs out."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: bool
        tick_index: int
        loop_point: Optional[int]

    test_cases: Tuple["TestSoundTick.TestCase", ...] = (
        TestCase(label="a one-shot within its envelope", tick_index=0, loop_point=None, expected=True),
        TestCase(
            label="a one-shot on its final tick",
            tick_index=ENVELOPE_TICKS - 1,
            loop_point=None,
            expected=True,
        ),
        TestCase(
            label="a one-shot past its envelope",
            tick_index=ENVELOPE_TICKS,
            loop_point=None,
            expected=False,
        ),
        TestCase(
            label="a looping voice past its envelope",
            tick_index=ENVELOPE_TICKS,
            loop_point=WHOLE_LOOP_POINT,
            expected=True,
        ),
        TestCase(
            label="a looping voice several passes on",
            tick_index=ENVELOPE_TICKS * 4 + 1,
            loop_point=WHOLE_LOOP_POINT,
            expected=True,
        ),
        TestCase(
            label="a voice circling its tail",
            tick_index=ENVELOPE_TICKS * 4,
            loop_point=TAIL_LOOP_POINT,
            expected=True,
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_whether_the_channel_still_sounds(self, test_case: TestCase) -> None:
        reading = _reading(test_case.loop_point)
        performance = ChannelPerformance(tick_index=test_case.tick_index)

        instruction = sound_tick(performance, reading)

        assert (instruction is not None) is test_case.expected

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_channel_moves_on_whether_or_not_it_sounds(self, test_case: TestCase) -> None:
        """A voice that has played out keeps counting, so the tick index states the song's time."""
        reading = _reading(test_case.loop_point)
        performance = ChannelPerformance(tick_index=test_case.tick_index)

        sound_tick(performance, reading)

        assert performance.tick_index == test_case.tick_index + 1

    def test_a_looping_voice_wraps_onto_the_instruction_the_pass_reaches(self) -> None:
        reading = _reading(WHOLE_LOOP_POINT)
        performance = ChannelPerformance()

        sounded = [sound_tick(performance, reading) for _ in range(ENVELOPE_TICKS * 2)]

        assert sounded[:ENVELOPE_TICKS] == sounded[ENVELOPE_TICKS:]

    def test_a_loop_point_leaves_the_opening_behind(self) -> None:
        """A voice repeating from a point plays its opening once, then circles the frames past it."""
        reading = _reading(TAIL_LOOP_POINT)
        performance = ChannelPerformance()

        sounded = [sound_tick(performance, reading) for _ in range(ENVELOPE_TICKS + 2)]

        assert sounded[:ENVELOPE_TICKS] == [reading.at(index) for index in range(ENVELOPE_TICKS)]
        assert sounded[ENVELOPE_TICKS:] == [sounded[TAIL_LOOP_POINT]] * 2

    def test_a_loop_point_past_the_frames_circles_the_last_one(self) -> None:
        reading = _reading(ENVELOPE_TICKS * 2)
        performance = ChannelPerformance(tick_index=ENVELOPE_TICKS * 3)

        assert sound_tick(performance, reading) == _reading(None).at(ENVELOPE_TICKS - 1)

    def test_the_row_bends_the_instruction_the_voice_holds(self) -> None:
        """The transpose and volume a row reached are applied to what the channel sounds."""
        reading = _reading(None)
        transpose = 7
        volume = MAX_VOLUME // 3
        performance = ChannelPerformance(transpose=transpose, volume=volume)

        instruction = sound_tick(performance, reading)

        held: Optional[InstructionUnion] = reading.instructions[0]
        assert isinstance(instruction, PulseInstruction)
        assert isinstance(held, PulseInstruction)
        assert instruction.pitch == held.pitch + transpose
        assert instruction.volume == round(held.volume * volume / MAX_VOLUME)
