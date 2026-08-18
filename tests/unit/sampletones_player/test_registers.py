from dataclasses import dataclass
from typing import Dict, Final, List, Tuple

import pytest

from sampletones_core.constants.general import (
    MAX_DUTY_CYCLE,
    MAX_PERIOD,
    MAX_PITCH,
    MAX_TIMER,
    MAX_VOLUME,
    MIN_PITCH,
)
from sampletones_core.instructions import (
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)
from sampletones_core.timers.arithmetic import frequency_to_timer
from sampletones_core.utils.frequencies import pitch_to_frequency
from sampletones_player.registers import (
    PulseRegisters,
    encode_noise,
    encode_pulse,
    encode_triangle,
)
from sampletones_player.specification.registers import MAX_REGISTER_VALUE, TIMER_HIGH_SHIFT
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase

TIMER_TABLE: Final[Dict[int, int]] = {
    pitch: frequency_to_timer(pitch_to_frequency(pitch)) for pitch in range(MIN_PITCH, MAX_PITCH + 1)
}

PULSE_TIMER_MUTE_FLOOR: Final[int] = 8
REFERENCE_PITCH: Final[int] = 69


def sounding_pulse(
    pitch: int,
    volume: int,
    duty_cycle: int,
) -> PulseInstruction:
    return PulseInstruction(
        on=True,
        pitch=pitch,
        volume=volume,
        duty_cycle=duty_cycle,
    )


def silent_pulse() -> PulseInstruction:
    return PulseInstruction.null_instruction()


class TestPulseTimerRange(BaseTestSuite):
    """Every pitch a channel may sound reaches a timer the hardware plays.

    The APU silences a pulse channel below timer 8 and the register holds 11 bits, so the
    playable pitch range has to land between those two bounds for the driver to sound it.
    """

    @pytest.mark.parametrize("pitch", [MIN_PITCH, REFERENCE_PITCH, MAX_PITCH])
    def test_timer_lies_within_the_audible_register_range(self, pitch: int) -> None:
        timer = TIMER_TABLE[pitch]
        assert PULSE_TIMER_MUTE_FLOOR <= timer <= MAX_TIMER

    def test_timer_splits_into_a_byte_and_three_bits(self) -> None:
        registers = encode_pulse([sounding_pulse(REFERENCE_PITCH, MAX_VOLUME, 0)], TIMER_TABLE)
        timer = TIMER_TABLE[REFERENCE_PITCH]
        assert registers[0].timer_low == timer & MAX_REGISTER_VALUE
        assert registers[0].timer_high == timer >> TIMER_HIGH_SHIFT


class TestTickRecord:
    """A tick states its values in the order the driver moves them to its channel."""

    def test_pulse_tick_states_control_then_timer(self) -> None:
        registers = encode_pulse([sounding_pulse(REFERENCE_PITCH, MAX_VOLUME, MAX_DUTY_CYCLE)], TIMER_TABLE)[0]
        timer = TIMER_TABLE[REFERENCE_PITCH]
        assert registers.values == (0xFF, timer & MAX_REGISTER_VALUE, timer >> TIMER_HIGH_SHIFT)

    def test_triangle_tick_states_the_counter_then_timer(self) -> None:
        registers = encode_triangle([TriangleInstruction(on=True, pitch=REFERENCE_PITCH)], TIMER_TABLE)[0]
        timer = TIMER_TABLE[REFERENCE_PITCH]
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
        instructions = [sounding_pulse(REFERENCE_PITCH, test_case.volume, test_case.duty_cycle)]
        registers = encode_pulse(instructions, TIMER_TABLE)
        assert registers[0].control == test_case.expected


class TestPulseRest:
    """A rest zeroes the level and keeps everything else the channel was holding.

    Holding the period across a rest is what lets the driver leave the timer's high byte
    untouched, and leaving it untouched is what keeps the waveform's phase running.
    """

    @staticmethod
    def encode_note_then_rest() -> List[PulseRegisters]:
        instructions = [
            sounding_pulse(REFERENCE_PITCH, MAX_VOLUME, MAX_DUTY_CYCLE),
            silent_pulse(),
        ]
        return encode_pulse(instructions, TIMER_TABLE)

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


class TestReleaseTick:
    """A sample that ends while sounding gains one closing tick that silences its channel."""

    def test_pulse_gains_a_silent_closing_tick(self) -> None:
        registers = encode_pulse([sounding_pulse(REFERENCE_PITCH, MAX_VOLUME, 0)], TIMER_TABLE)
        assert len(registers) == 2
        assert registers[-1].control & 0x0F == 0

    def test_a_sample_ending_in_a_rest_gains_no_extra_tick(self) -> None:
        instructions = [sounding_pulse(REFERENCE_PITCH, MAX_VOLUME, 0), silent_pulse()]
        assert len(encode_pulse(instructions, TIMER_TABLE)) == 2

    def test_no_instructions_encode_to_no_ticks(self) -> None:
        assert encode_pulse([], TIMER_TABLE) == []


class TestEncodeTriangle:
    """The triangle states whether it sounds through the linear counter's reload value.

    The control bit stays set so the counter reloads every frame, and a reload of zero is
    what holds the channel silent.
    """

    def test_sounding_tick_reloads_the_counter_fully(self) -> None:
        registers = encode_triangle([TriangleInstruction(on=True, pitch=REFERENCE_PITCH)], TIMER_TABLE)
        assert registers[0].linear_counter == 0xFF

    def test_resting_tick_reloads_the_counter_to_zero(self) -> None:
        instructions = [
            TriangleInstruction(on=True, pitch=REFERENCE_PITCH),
            TriangleInstruction.null_instruction(),
        ]
        registers = encode_triangle(instructions, TIMER_TABLE)
        assert registers[1].linear_counter == 0x80

    def test_rest_keeps_the_timer(self) -> None:
        instructions = [
            TriangleInstruction(on=True, pitch=REFERENCE_PITCH),
            TriangleInstruction.null_instruction(),
        ]
        sounding, resting = encode_triangle(instructions, TIMER_TABLE)[:2]
        assert (resting.timer_low, resting.timer_high) == (sounding.timer_low, sounding.timer_high)

    def test_triangle_shares_the_pulse_timer(self) -> None:
        triangle = encode_triangle([TriangleInstruction(on=True, pitch=REFERENCE_PITCH)], TIMER_TABLE)
        pulse = encode_pulse([sounding_pulse(REFERENCE_PITCH, MAX_VOLUME, 0)], TIMER_TABLE)
        assert (triangle[0].timer_low, triangle[0].timer_high) == (pulse[0].timer_low, pulse[0].timer_high)


class TestEncodeNoise(BaseTestSuite):
    """The project counts noise periods from the slowest and the register from the fastest."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: Tuple[int, int]
        period: int
        short: bool

        @property
        def label(self) -> str:
            mode = "short" if self.short else "normal"
            return f"period_{self.period}_{mode}"

    test_cases = (
        TestCase(period=0, short=False, expected=(0x3F, MAX_PERIOD)),
        TestCase(period=MAX_PERIOD, short=False, expected=(0x3F, 0)),
        TestCase(period=0, short=True, expected=(0x3F, 0x80 | MAX_PERIOD)),
        TestCase(period=MAX_PERIOD, short=True, expected=(0x3F, 0x80)),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_registers_match(self, test_case: TestCase) -> None:
        instruction = NoiseInstruction(
            on=True,
            period=test_case.period,
            volume=MAX_VOLUME,
            short=test_case.short,
        )
        registers = encode_noise([instruction])
        assert registers[0].values == test_case.expected

    def test_rest_clears_the_volume_and_keeps_the_period(self) -> None:
        instructions = [
            NoiseInstruction(on=True, period=4, volume=MAX_VOLUME, short=False),
            NoiseInstruction.null_instruction(),
        ]
        sounding, resting = encode_noise(instructions)[:2]
        assert resting.control & 0x0F == 0
        assert resting.period == sounding.period
