from typing import Final, List

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import (
    InstructionUnion,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)
from sampletones_player.registers.channel import channel_instructions, channel_registers
from sampletones_player.specification.registers import (
    TRIANGLE_COUNTER_CONTROL,
    TRIANGLE_SOUNDING_RELOAD,
)
from tests.suite.player import (
    PLAYER_FULL_VOLUME,
    PLAYER_REFERENCE_PITCH,
    PLAYER_TIMER_TABLE,
    sounding_pulse,
)

SOUNDING_TICKS: Final[int] = 4
BASS_PITCH: Final[int] = 45
NOISE_PERIOD: Final[int] = 10
NOISE_VOLUME: Final[int] = 8


def melody() -> List[InstructionUnion]:
    return [sounding_pulse(PLAYER_REFERENCE_PITCH, PLAYER_FULL_VOLUME, 0) for _ in range(SOUNDING_TICKS)]


class TestChannelInstructions:
    """A channel's stream read as the instruction type its encoder takes."""

    def test_a_stream_of_the_channels_own_type_passes_through(self) -> None:
        instructions = melody()
        assert channel_instructions(instructions, PulseInstruction) == instructions

    def test_a_channel_describing_no_frame_rests_for_a_tick(self) -> None:
        assert channel_instructions([], PulseInstruction) == [PulseInstruction.null_instruction()]

    def test_a_resting_channel_rests_in_its_own_type(self) -> None:
        assert channel_instructions([], NoiseInstruction) == [NoiseInstruction.null_instruction()]

    def test_a_stream_of_another_channels_type_raises(self) -> None:
        with pytest.raises(TypeError):
            channel_instructions(melody(), TriangleInstruction)


class TestChannelRegisters:
    """Naming the channel is the whole of what it takes to encode a stream."""

    def test_a_sounding_channel_carries_a_tick_per_instruction_and_a_release(self) -> None:
        registers = channel_registers(ChannelName.PULSE1, {ChannelName.PULSE1: melody()}, PLAYER_TIMER_TABLE)
        assert len(registers) == SOUNDING_TICKS + 1

    def test_a_channel_the_song_leaves_out_rests_for_a_tick(self) -> None:
        assert len(channel_registers(ChannelName.PULSE2, {}, PLAYER_TIMER_TABLE)) == 1

    def test_a_pitch_reaches_the_timer_the_table_states(self) -> None:
        registers = channel_registers(ChannelName.PULSE1, {ChannelName.PULSE1: melody()}, PLAYER_TIMER_TABLE)
        timer = PLAYER_TIMER_TABLE[PLAYER_REFERENCE_PITCH]
        assert registers[0].values[1:] == (timer & 0xFF, timer >> 8)

    def test_the_triangle_channel_answers_in_its_own_registers(self) -> None:
        instructions: List[InstructionUnion] = [TriangleInstruction(on=True, pitch=BASS_PITCH)]
        registers = channel_registers(
            ChannelName.TRIANGLE,
            {ChannelName.TRIANGLE: instructions},
            PLAYER_TIMER_TABLE,
        )
        assert registers[0].linear_counter == TRIANGLE_COUNTER_CONTROL | TRIANGLE_SOUNDING_RELOAD

    def test_the_noise_channel_answers_in_its_own_registers(self) -> None:
        instructions: List[InstructionUnion] = [
            NoiseInstruction(on=True, period=NOISE_PERIOD, volume=NOISE_VOLUME, short=False),
        ]
        registers = channel_registers(
            ChannelName.NOISE,
            {ChannelName.NOISE: instructions},
            PLAYER_TIMER_TABLE,
        )
        assert registers[0].control & 0x0F == NOISE_VOLUME

    def test_a_channel_holding_another_channels_instructions_raises(self) -> None:
        with pytest.raises(TypeError):
            channel_registers(ChannelName.TRIANGLE, {ChannelName.TRIANGLE: melody()}, PLAYER_TIMER_TABLE)
