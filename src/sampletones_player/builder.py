from typing import Dict, List, Mapping, Optional, Sequence, Type

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.instructions import (
    InstructionT,
    InstructionUnion,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.timers.utils import get_timer_table
from sampletones_player.clock.schedule import PlaySchedule
from sampletones_player.registers.noise import NoiseRegisters
from sampletones_player.registers.pulse import PulseRegisters
from sampletones_player.registers.streams import ChannelStreams
from sampletones_player.registers.triangle import TriangleRegisters
from sampletones_player.song import Song


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


def streams_from_instructions(
    instructions: Mapping[GeneratorName, Sequence[InstructionUnion]],
    timer_table: Dict[int, int],
) -> ChannelStreams:
    """Encodes every channel's instructions into the register values its ticks write.

    The song covers all four channels, so a channel the mapping leaves out rests through it,
    the same as one whose stream describes no frame.

    Args:
        instructions: The stream each channel carries.
        timer_table: The timer register value each pitch sounds at.

    Returns:
        ChannelStreams: The four streams the driver plays.

    Raises:
        TypeError: If a channel's stream holds an instruction another channel sounds.
    """
    pulse1 = channel_instructions(
        instructions.get(GeneratorName.PULSE1, ()),
        PulseInstruction,
    )
    pulse2 = channel_instructions(
        instructions.get(GeneratorName.PULSE2, ()),
        PulseInstruction,
    )
    triangle = channel_instructions(
        instructions.get(GeneratorName.TRIANGLE, ()),
        TriangleInstruction,
    )
    noise = channel_instructions(
        instructions.get(GeneratorName.NOISE, ()),
        NoiseInstruction,
    )

    return ChannelStreams(
        pulse1=tuple(PulseRegisters.from_instructions(pulse1, timer_table)),
        pulse2=tuple(PulseRegisters.from_instructions(pulse2, timer_table)),
        triangle=tuple(TriangleRegisters.from_instructions(triangle, timer_table)),
        noise=tuple(NoiseRegisters.from_instructions(noise)),
    )


def song_from_reconstruction(
    reconstruction: Reconstruction,
    loop_tick: Optional[int],
) -> Song:
    """Builds the song the console plays a reconstruction as.

    The reconstruction's own configuration carries both halves of the answer: the pitches it was
    built against become timers through the very table its generators render from, and the rate
    it was built at becomes the schedule the driver re-clocks the streams by.

    Args:
        reconstruction: The reconstruction to play.
        loop_tick: The tick the song returns to once it ends, or ``None`` where it stops there.

    Returns:
        Song: The streams, the clock and the loop point as the player holds them.

    Raises:
        TypeError: If a channel's stream holds an instruction another channel sounds.
        ValueError: If ``loop_tick`` lies outside the song's ticks.
    """
    return Song(
        streams=streams_from_instructions(
            reconstruction.instructions,
            get_timer_table(reconstruction.config),
        ),
        schedule=PlaySchedule.from_parameters(reconstruction.config.nes_frequency),
        loop_tick=loop_tick,
    )
