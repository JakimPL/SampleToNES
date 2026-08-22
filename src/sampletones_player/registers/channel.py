from typing import Dict, List, Literal, Mapping, Sequence, Tuple, Type, overload

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import (
    InstructionT,
    InstructionUnion,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)
from sampletones_player.registers.base import ChannelRegisters
from sampletones_player.registers.noise import NoiseRegisters
from sampletones_player.registers.pulse import PulseRegisters
from sampletones_player.registers.triangle import TriangleRegisters


def channel_instructions(
    instructions: Sequence[InstructionUnion],
    instruction_type: Type[InstructionT],
) -> List[InstructionT]:
    """One channel's stream, read as the instruction type that channel sounds.

    A reconstruction holds a stream for every channel, and a channel standing by holds one
    describing no frame. Such a channel reaches the player resting for a single tick, which is
    the shortest stream a song lays its records out from.

    Args:
        instructions: The channel's stream, as the reconstruction holds it.
        instruction_type: The instruction type the channel's encoder reads.

    Returns:
        List[InstructionT]: The stream, covering at least one tick.

    Raises:
        TypeError: If the stream holds an instruction another channel sounds.
    """
    typed: List[InstructionT] = []
    for instruction in instructions:
        if not isinstance(instruction, instruction_type):
            raise TypeError(
                f"a {instruction_type.__name__} stream holds {type(instruction).__name__} "
                f"{instruction.name}, which another channel sounds"
            )

        typed.append(instruction)

    if typed:
        return typed

    resting: InstructionT = instruction_type.null_instruction()
    return [resting]


@overload
def channel_registers(
    channel: Literal[ChannelName.PULSE1, ChannelName.PULSE2],
    instructions: Mapping[ChannelName, Sequence[InstructionUnion]],
    timer_table: Dict[int, int],
) -> Tuple[PulseRegisters, ...]: ...


@overload
def channel_registers(
    channel: Literal[ChannelName.TRIANGLE],
    instructions: Mapping[ChannelName, Sequence[InstructionUnion]],
    timer_table: Dict[int, int],
) -> Tuple[TriangleRegisters, ...]: ...


@overload
def channel_registers(
    channel: Literal[ChannelName.NOISE],
    instructions: Mapping[ChannelName, Sequence[InstructionUnion]],
    timer_table: Dict[int, int],
) -> Tuple[NoiseRegisters, ...]: ...


@overload
def channel_registers(
    channel: ChannelName,
    instructions: Mapping[ChannelName, Sequence[InstructionUnion]],
    timer_table: Dict[int, int],
) -> Tuple[ChannelRegisters, ...]: ...


def channel_registers(
    channel: ChannelName,
    instructions: Mapping[ChannelName, Sequence[InstructionUnion]],
    timer_table: Dict[int, int],
) -> Tuple[ChannelRegisters, ...]:
    """Encodes one channel's instructions into the register values its ticks write.

    The channel decides all three halves of the answer: which stream of the song it plays, the
    instruction type that stream is read as, and the register set those instructions become.
    Naming the channel is therefore the whole of what a caller states, and a channel the song
    leaves out rests through it.

    Args:
        channel: The channel to encode.
        instructions: The per-tick instructions each channel carries.
        timer_table: The timer register value each pitch sounds at.

    Returns:
        Tuple[ChannelRegisters, ...]: One register set per tick, covering at least one tick.

    Raises:
        TypeError: If the channel's stream holds an instruction another channel sounds.
    """
    played = instructions.get(channel, ())
    match channel:
        case ChannelName.PULSE1 | ChannelName.PULSE2:
            pulse = channel_instructions(played, PulseInstruction)
            return tuple(PulseRegisters.from_instructions(pulse, timer_table))
        case ChannelName.TRIANGLE:
            triangle = channel_instructions(played, TriangleInstruction)
            return tuple(TriangleRegisters.from_instructions(triangle, timer_table))
        case ChannelName.NOISE:
            noise = channel_instructions(played, NoiseInstruction)
            return tuple(NoiseRegisters.from_instructions(noise))
