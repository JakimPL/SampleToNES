from dataclasses import dataclass
from typing import Optional, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.features.envelope import Envelope
from sampletones_core.instructions import InstructionUnion, PulseInstruction
from sampletones_core.performance import ChannelPerformance, VoiceReading, sound_tick
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.sample import Sample
from sampletones_core.project.voices.voice import VoiceUnion
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.performance import make_pulse_reconstruction

ENVELOPE_TICKS: int = 3
SOUNDING_PITCH: int = 60


def _reading(*, sustaining: bool = False) -> VoiceReading:
    """A pulse voice over a three-tick envelope, read the way a channel reads it.

    A recording sounds the frames its conversion found; an instrument writing the same three
    ticks holds its final values past them, so the two kinds part company where the written
    run ends.
    """
    voice: VoiceUnion = _instrument() if sustaining else _sample()
    reading = VoiceReading.read(voice, ChannelName.PULSE1)
    assert reading is not None
    return reading


def _sample() -> Sample:
    return Sample(
        name="lead",
        reconstruction=make_pulse_reconstruction(pitch=SOUNDING_PITCH, count=ENVELOPE_TICKS),
    )


def _instrument() -> Instrument:
    return Instrument(
        name="lead",
        envelopes=InstrumentEnvelopes(volume=Envelope[int](items=(MAX_VOLUME,) * ENVELOPE_TICKS)),
        initial_pitch=SOUNDING_PITCH,
    )


class TestSoundTick(BaseTestSuite):
    """Which of a voice's instructions a channel reaches, and where it runs out."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: bool
        tick_index: int
        sustaining: bool

    test_cases: Tuple["TestSoundTick.TestCase", ...] = (
        TestCase(label="a recording within its frames", tick_index=0, sustaining=False, expected=True),
        TestCase(
            label="a recording on its final frame",
            tick_index=ENVELOPE_TICKS - 1,
            sustaining=False,
            expected=True,
        ),
        TestCase(
            label="a recording past its frames",
            tick_index=ENVELOPE_TICKS,
            sustaining=False,
            expected=False,
        ),
        TestCase(
            label="an instrument past its envelopes",
            tick_index=ENVELOPE_TICKS,
            sustaining=True,
            expected=True,
        ),
        TestCase(
            label="an instrument several passes on",
            tick_index=ENVELOPE_TICKS * 4 + 1,
            sustaining=True,
            expected=True,
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_whether_the_channel_still_sounds(self, test_case: TestCase) -> None:
        reading = _reading(sustaining=test_case.sustaining)
        performance = ChannelPerformance(tick_index=test_case.tick_index)

        instruction = sound_tick(performance, reading)

        assert (instruction is not None) is test_case.expected

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_channel_moves_on_whether_or_not_it_sounds(self, test_case: TestCase) -> None:
        """A voice that has played out keeps counting, so the tick index states the song's time."""
        reading = _reading(sustaining=test_case.sustaining)
        performance = ChannelPerformance(tick_index=test_case.tick_index)

        sound_tick(performance, reading)

        assert performance.tick_index == test_case.tick_index + 1

    def test_a_recording_rests_once_its_frames_are_played(self) -> None:
        """A recording is a fixed run, so a note holding past it leaves the channel silent."""
        reading = _reading()
        performance = ChannelPerformance()

        sounded = [sound_tick(performance, reading) for _ in range(ENVELOPE_TICKS * 2)]

        assert sounded[ENVELOPE_TICKS:] == [None] * ENVELOPE_TICKS

    def test_an_instrument_goes_on_holding_its_final_frame(self) -> None:
        """An instrument's dimensions hold their last item, so the frame it ended on sounds on."""
        reading = _reading(sustaining=True)
        performance = ChannelPerformance()

        sounded = [sound_tick(performance, reading) for _ in range(ENVELOPE_TICKS * 2)]

        assert sounded[ENVELOPE_TICKS:] == [sounded[ENVELOPE_TICKS - 1]] * ENVELOPE_TICKS

    def test_the_row_bends_the_instruction_the_voice_holds(self) -> None:
        """The transpose and volume a row reached are applied to what the channel sounds."""
        reading = _reading()
        transpose = 7
        volume = MAX_VOLUME // 3
        performance = ChannelPerformance(transpose=transpose, volume=volume)

        instruction = sound_tick(performance, reading)

        held: Optional[InstructionUnion] = reading.instructions[0]
        assert isinstance(instruction, PulseInstruction)
        assert isinstance(held, PulseInstruction)
        assert instruction.pitch == held.pitch + transpose
        assert instruction.volume == round(held.volume * volume / MAX_VOLUME)
