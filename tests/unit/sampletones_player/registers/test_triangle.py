import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.generators.implementation.triangle import TriangleGenerator
from sampletones_core.instructions import TriangleInstruction
from sampletones_player.registers.pulse import PulseRegisters
from sampletones_player.registers.triangle import TriangleRegisters
from sampletones_player.specification.registers import MAX_REGISTER_VALUE, TIMER_HIGH_SHIFT
from tests.suite.player import PLAYER_REFERENCE_PITCH, PLAYER_TIMER_TABLE, sounding_pulse


def sounding_triangle() -> TriangleInstruction:
    return TriangleInstruction(on=True, pitch=PLAYER_REFERENCE_PITCH)


class TestTriangleTickRecord:
    """A tick states its values in the order the driver moves them to its channel."""

    def test_a_tick_states_the_counter_then_timer(self) -> None:
        registers = TriangleRegisters.from_instructions([sounding_triangle()], PLAYER_TIMER_TABLE)[0]
        timer = PLAYER_TIMER_TABLE[PLAYER_REFERENCE_PITCH]
        assert registers.values == (0xFF, timer & MAX_REGISTER_VALUE, timer >> TIMER_HIGH_SHIFT)


class TestTriangleRegisters:
    """The triangle states whether it sounds through the linear counter's reload value.

    The control bit stays set so the counter reloads every frame, and a reload of zero is
    what holds the channel silent.
    """

    def test_sounding_tick_reloads_the_counter_fully(self) -> None:
        registers = TriangleRegisters.from_instructions([sounding_triangle()], PLAYER_TIMER_TABLE)
        assert registers[0].linear_counter == 0xFF

    def test_resting_tick_reloads_the_counter_to_zero(self) -> None:
        instructions = [sounding_triangle(), TriangleInstruction.null_instruction()]
        registers = TriangleRegisters.from_instructions(instructions, PLAYER_TIMER_TABLE)
        assert registers[1].linear_counter == 0x80

    def test_rest_keeps_the_timer(self) -> None:
        instructions = [sounding_triangle(), TriangleInstruction.null_instruction()]
        sounding, resting = TriangleRegisters.from_instructions(instructions, PLAYER_TIMER_TABLE)[:2]
        assert (resting.timer_low, resting.timer_high) == (sounding.timer_low, sounding.timer_high)

    def test_triangle_shares_the_pulse_timer(self) -> None:
        triangle = TriangleRegisters.from_instructions([sounding_triangle()], PLAYER_TIMER_TABLE)
        pulse = PulseRegisters.from_instructions(
            [sounding_pulse(PLAYER_REFERENCE_PITCH, MAX_VOLUME, 0)],
            PLAYER_TIMER_TABLE,
        )
        assert (triangle[0].timer_low, triangle[0].timer_high) == (pulse[0].timer_low, pulse[0].timer_high)


class TestTriangleBend:
    """A bent frame's timer is the very divider the triangle generator renders it at."""

    @pytest.mark.parametrize(
        ("detune", "coarse_detune"),
        [(4, 0), (-6, 2), (0, -3)],
        ids=lambda bend: f"{bend:+d}",
    )
    def test_the_timer_is_the_divider_the_generator_sounds(self, detune: int, coarse_detune: int) -> None:
        instruction = TriangleInstruction(
            on=True,
            pitch=PLAYER_REFERENCE_PITCH,
            detune=detune,
            coarse_detune=coarse_detune,
        )
        registers = TriangleRegisters.from_instructions([instruction], PLAYER_TIMER_TABLE)[0]
        expected = TriangleGenerator(Config(), ChannelName.TRIANGLE).get_timer(
            instruction.pitch,
            instruction.timer_offset,
        )
        assert (registers.timer_low, registers.timer_high) == (
            expected & MAX_REGISTER_VALUE,
            expected >> TIMER_HIGH_SHIFT,
        )

    def test_a_rest_holds_the_bent_divider(self) -> None:
        instructions = [
            TriangleInstruction(on=True, pitch=PLAYER_REFERENCE_PITCH, detune=11),
            TriangleInstruction.null_instruction(),
        ]
        sounding, resting = TriangleRegisters.from_instructions(instructions, PLAYER_TIMER_TABLE)[:2]
        assert (resting.timer_low, resting.timer_high) == (sounding.timer_low, sounding.timer_high)
