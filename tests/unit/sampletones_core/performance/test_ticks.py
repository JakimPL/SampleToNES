from dataclasses import dataclass
from typing import List, Optional, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.instructions import InstructionUnion, PulseInstruction
from sampletones_core.performance import ChannelPerformance, SampleVoice, sound_tick
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.performance import make_pulse_reconstruction

ENVELOPE_TICKS: int = 3
SOUNDING_PITCH: int = 60


def _voice() -> Tuple[SampleVoice, List[InstructionUnion]]:
    """A pulse voice over a three-tick envelope, read the way a channel reads it."""
    reconstruction = make_pulse_reconstruction(pitch=SOUNDING_PITCH, count=ENVELOPE_TICKS)
    return (
        SampleVoice.read(reconstruction, ChannelName.PULSE1),
        reconstruction.instructions[ChannelName.PULSE1],
    )


class TestSoundTick(BaseTestSuite):
    """Which of a sample's instructions a channel reaches, and where it runs out."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: bool
        tick_index: int
        loop: bool

    test_cases: Tuple["TestSoundTick.TestCase", ...] = (
        TestCase(label="a one-shot within its envelope", tick_index=0, loop=False, expected=True),
        TestCase(
            label="a one-shot on its final tick",
            tick_index=ENVELOPE_TICKS - 1,
            loop=False,
            expected=True,
        ),
        TestCase(
            label="a one-shot past its envelope",
            tick_index=ENVELOPE_TICKS,
            loop=False,
            expected=False,
        ),
        TestCase(
            label="a looping sample past its envelope",
            tick_index=ENVELOPE_TICKS,
            loop=True,
            expected=True,
        ),
        TestCase(
            label="a looping sample several passes on",
            tick_index=ENVELOPE_TICKS * 4 + 1,
            loop=True,
            expected=True,
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_whether_the_channel_still_sounds(self, test_case: TestCase) -> None:
        voice, instructions = _voice()
        performance = ChannelPerformance(tick_index=test_case.tick_index)

        instruction = sound_tick(performance, instructions, loop=test_case.loop, voice=voice)

        assert (instruction is not None) is test_case.expected

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_channel_moves_on_whether_or_not_it_sounds(self, test_case: TestCase) -> None:
        """A sample that has played out keeps counting, so the tick index states the song's time."""
        voice, instructions = _voice()
        performance = ChannelPerformance(tick_index=test_case.tick_index)

        sound_tick(performance, instructions, loop=test_case.loop, voice=voice)

        assert performance.tick_index == test_case.tick_index + 1

    def test_a_looping_sample_wraps_onto_the_instruction_the_pass_reaches(self) -> None:
        voice, instructions = _voice()
        performance = ChannelPerformance()

        sounded = [sound_tick(performance, instructions, loop=True, voice=voice) for _ in range(ENVELOPE_TICKS * 2)]

        assert sounded[:ENVELOPE_TICKS] == sounded[ENVELOPE_TICKS:]

    def test_the_row_bends_the_instruction_the_sample_holds(self) -> None:
        """The transpose and volume a row reached are applied to what the channel sounds."""
        voice, instructions = _voice()
        transpose = 7
        volume = MAX_VOLUME // 3
        performance = ChannelPerformance(transpose=transpose, volume=volume)

        instruction = sound_tick(performance, instructions, loop=False, voice=voice)

        held: Optional[InstructionUnion] = instructions[0]
        assert isinstance(instruction, PulseInstruction)
        assert isinstance(held, PulseInstruction)
        assert instruction.pitch == held.pitch + transpose
        assert instruction.volume == round(held.volume * volume / MAX_VOLUME)
