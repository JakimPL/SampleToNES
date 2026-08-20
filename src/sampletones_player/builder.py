from typing import Dict, Final, List, Mapping, Optional, Sequence, Type

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.maps import CHANNEL_TO_EXPORTER_MAP
from sampletones_core.exports.request import InstrumentExport, SampleExport
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

SONG_START: Final[int] = 0


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
    instructions: Mapping[ChannelName, Sequence[InstructionUnion]],
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
        instructions.get(ChannelName.PULSE1, ()),
        PulseInstruction,
    )
    pulse2 = channel_instructions(
        instructions.get(ChannelName.PULSE2, ()),
        PulseInstruction,
    )
    triangle = channel_instructions(
        instructions.get(ChannelName.TRIANGLE, ()),
        TriangleInstruction,
    )
    noise = channel_instructions(
        instructions.get(ChannelName.NOISE, ()),
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
            get_timer_table(reconstruction.config.tuning),
        ),
        schedule=PlaySchedule.from_parameters(reconstruction.config.nes_frequency),
        loop_tick=loop_tick,
    )


def instructions_from_instruments(
    instruments: Sequence[InstrumentExport],
) -> Dict[ChannelName, Sequence[InstructionUnion]]:
    """Reads every channel slice of an export request back as instructions.

    A request describes each slice as the envelopes an instrument carries, which is the form a
    tracker reads it in. The console sounds instructions instead, so each slice is walked back
    through the exporter belonging to the channel it was reconstructed for.

    Args:
        instruments: The slices to sound.

    Returns:
        Dict[ChannelName, Sequence[InstructionUnion]]: The stream each channel carries.

    Raises:
        ValueError: If two slices name the same channel, which the console sounds one of.
    """
    instructions: Dict[ChannelName, Sequence[InstructionUnion]] = {}
    for instrument in instruments:
        if instrument.channel in instructions:
            raise ValueError(f"Channel '{instrument.channel}' carries two slices, and the console sounds one")

        exporter = CHANNEL_TO_EXPORTER_MAP[instrument.channel]
        instructions[instrument.channel] = exporter.from_features(instrument.features)

    return instructions


def loop_tick_from_instruments(instruments: Sequence[InstrumentExport]) -> Optional[int]:
    """The tick a request's song returns to once it ends.

    A song repeats from its first tick where every slice it carries repeats, and ends at its
    last tick where any slice plays its envelopes once.

    Args:
        instruments: The slices the song carries.

    Returns:
        Optional[int]: The tick to return to, or ``None`` where the song stops at its end.
    """
    if instruments and all(instrument.loop for instrument in instruments):
        return SONG_START

    return None


def song_from_sample(request: SampleExport) -> Song:
    """Builds the song the console plays an export request as.

    Every slice sounds at once on the channel it was reconstructed for, and the request states
    both halves of what that takes: the tuning its pitches are measured from, and the rate its
    envelopes advance at, which the driver re-clocks to the rate the console calls it at.

    Args:
        request: The slices to play together.

    Returns:
        Song: The streams, the clock and the loop point as the player holds them.

    Raises:
        TypeError: If a channel's stream holds an instruction another channel sounds.
        ValueError: If two slices name the same channel.
    """
    return Song(
        streams=streams_from_instructions(
            instructions_from_instruments(request.instruments),
            get_timer_table(request.tuning),
        ),
        schedule=PlaySchedule.from_parameters(request.nes_frequency),
        loop_tick=loop_tick_from_instruments(request.instruments),
    )
