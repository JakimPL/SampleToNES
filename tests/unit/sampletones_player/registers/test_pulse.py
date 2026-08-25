from dataclasses import dataclass
from typing import List

import pytest

from sampletones_core.constants.general import (
    MAX_DUTY_CYCLE,
    MAX_PITCH,
    MAX_TIMER,
    MAX_VOLUME,
    MIN_PITCH,
)
from sampletones_player.registers.pulse import PulseRegisters
from sampletones_player.specification.registers import MAX_REGISTER_VALUE, TIMER_HIGH_SHIFT
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase
from tests.suite.player import (
    PLAYER_PULSE_TIMER_MUTE_FLOOR,
    PLAYER_REFERENCE_PITCH,
    PLAYER_TIMER_TABLE,
    silent_pulse,
    sounding_pulse,
)


class TestPulseTimerRange(BaseTestSuite):
    """Every pitch a channel may sound reaches a timer the hardware plays.

    The APU silences a pulse channel below timer 8 and the register holds 11 bits, so the
    playable pitch range has to land between those two bounds for the driver to sound it.
    """

    @pytest.mark.parametrize("pitch", [MIN_PITCH, PLAYER_REFERENCE_PITCH, MAX_PITCH])
    def test_timer_lies_within_the_audible_register_range(self, pitch: int) -> None:
        timer = PLAYER_TIMER_TABLE[pitch]
        assert PLAYER_PULSE_TIMER_MUTE_FLOOR <= timer <= MAX_TIMER

    def test_timer_splits_into_a_byte_and_three_bits(self) -> None:
        instructions = [sounding_pulse(PLAYER_REFERENCE_PITCH, MAX_VOLUME, 0)]
        registers = PulseRegisters.from_instructions(instructions, PLAYER_TIMER_TABLE)
        timer = PLAYER_TIMER_TABLE[PLAYER_REFERENCE_PITCH]
        assert registers[0].timer_low == timer & MAX_REGISTER_VALUE
        assert registers[0].timer_high == timer >> TIMER_HIGH_SHIFT


class TestPulseTickRecord:
    """A tick states its values in the order the driver moves them to its channel."""

    def test_a_tick_states_control_then_timer(self) -> None:
        instructions = [sounding_pulse(PLAYER_REFERENCE_PITCH, MAX_VOLUME, MAX_DUTY_CYCLE)]
        registers = PulseRegisters.from_instructions(instructions, PLAYER_TIMER_TABLE)[0]
        timer = PLAYER_TIMER_TABLE[PLAYER_REFERENCE_PITCH]
        assert registers.values == (0xFF, timer & MAX_REGISTER_VALUE, timer >> TIMER_HIGH_SHIFT)


class TestPulseControlByte(BaseTestSuite):
    """The expected bytes are the values the APU reads from ``$4000``.

    A duty cycle occupies the top two bits, the length-halt and constant-volume bits sit
    below them, and the level fills the low nibble.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: int
        duty_cycle: int
        volume: int

        @property
        def label(self) -> str:
            return f"duty_{self.duty_cycle}_volume_{self.volume}"

    test_cases = (
        TestCase(duty_cycle=0, volume=MAX_VOLUME, expected=0x3F),
        TestCase(duty_cycle=1, volume=MAX_VOLUME, expected=0x7F),
        TestCase(duty_cycle=2, volume=MAX_VOLUME, expected=0xBF),
        TestCase(duty_cycle=MAX_DUTY_CYCLE, volume=MAX_VOLUME, expected=0xFF),
        TestCase(duty_cycle=2, volume=0, expected=0xB0),
        TestCase(duty_cycle=0, volume=1, expected=0x31),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_control_byte_matches(self, test_case: TestCase) -> None:
        instructions = [sounding_pulse(PLAYER_REFERENCE_PITCH, test_case.volume, test_case.duty_cycle)]
        registers = PulseRegisters.from_instructions(instructions, PLAYER_TIMER_TABLE)
        assert registers[0].control == test_case.expected


class TestPulseRest:
    """A rest zeroes the level and keeps everything else the channel was holding.

    Holding the period across a rest is what lets the driver leave the timer's high byte
    untouched, and leaving it untouched is what keeps the waveform's phase running.
    """

    @staticmethod
    def encode_note_then_rest() -> List[PulseRegisters]:
        instructions = [
            sounding_pulse(PLAYER_REFERENCE_PITCH, MAX_VOLUME, MAX_DUTY_CYCLE),
            silent_pulse(),
        ]
        return PulseRegisters.from_instructions(instructions, PLAYER_TIMER_TABLE)

    def test_rest_clears_the_volume_nibble(self) -> None:
        sounding, resting = self.encode_note_then_rest()[:2]
        assert sounding.control & 0x0F == MAX_VOLUME
        assert resting.control & 0x0F == 0

    def test_rest_keeps_the_duty_cycle(self) -> None:
        sounding, resting = self.encode_note_then_rest()[:2]
        assert resting.control & 0xF0 == sounding.control & 0xF0

    def test_rest_keeps_the_timer(self) -> None:
        sounding, resting = self.encode_note_then_rest()[:2]
        assert (resting.timer_low, resting.timer_high) == (sounding.timer_low, sounding.timer_high)


class TestPulseReleaseTick:
    """A sample that ends while sounding gains one closing tick that silences its channel."""

    def test_pulse_gains_a_silent_closing_tick(self) -> None:
        instructions = [sounding_pulse(PLAYER_REFERENCE_PITCH, MAX_VOLUME, 0)]
        registers = PulseRegisters.from_instructions(instructions, PLAYER_TIMER_TABLE)
        assert len(registers) == 2
        assert registers[-1].control & 0x0F == 0

    def test_a_sample_ending_in_a_rest_gains_no_extra_tick(self) -> None:
        instructions = [sounding_pulse(PLAYER_REFERENCE_PITCH, MAX_VOLUME, 0), silent_pulse()]
        assert len(PulseRegisters.from_instructions(instructions, PLAYER_TIMER_TABLE)) == 2

    def test_no_instructions_encode_to_no_ticks(self) -> None:
        assert PulseRegisters.from_instructions([], PLAYER_TIMER_TABLE) == []
