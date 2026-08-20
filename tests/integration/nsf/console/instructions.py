from typing import Dict, Final, List, Mapping, Tuple

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.constants.general import MAX_PERIOD, MAX_VOLUME
from sampletones_core.instructions import (
    InstructionUnion,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)
from sampletones_player.specification.channels import CHANNEL_REGISTER_ADDRESSES
from sampletones_player.specification.registers import (
    DUTY_CYCLE_SHIFT,
    NOISE_MODE_SHIFT,
    TIMER_HIGH_SHIFT,
    TRIANGLE_COUNTER_CONTROL,
    TRIANGLE_SOUNDING_RELOAD,
)
from sampletones_player.trace.trace import RegisterTrace
from tests.integration.nsf.console.machine import register_file

TRIANGLE_SOUNDING: Final[int] = TRIANGLE_COUNTER_CONTROL | TRIANGLE_SOUNDING_RELOAD


def channel_values(registers: Mapping[int, int], channel: GeneratorName) -> Tuple[int, ...]:
    """The values standing in one channel's registers, in the order the driver writes them."""
    return tuple(registers[address] for address in CHANNEL_REGISTER_ADDRESSES[channel])


def timer_value(timer_low: int, timer_high: int) -> int:
    """The period the two halves of a channel's timer carry together."""
    return (timer_high << TIMER_HIGH_SHIFT) | timer_low


def pulse_instruction(
    registers: Mapping[int, int],
    channel: GeneratorName,
    pitches: Mapping[int, int],
) -> PulseInstruction:
    """The instruction a pulse channel's registers sound.

    Volume rides in the control byte's low nibble and the duty cycle in its top two bits, so a
    level of zero is what marks the tick a rest — the pitch and timbre standing there are the ones
    the channel was holding when it stopped sounding.

    Args:
        registers: The whole register file at a tick.
        channel: Which pulse channel to read.
        pitches: The pitch each timer value belongs to.

    Returns:
        PulseInstruction: The frame the channel plays.

    Raises:
        KeyError: If the timer standing there belongs to no pitch the configuration covers.
    """
    control, timer_low, timer_high = channel_values(registers, channel)
    volume = control & MAX_VOLUME
    return PulseInstruction(
        on=volume > 0,
        pitch=pitches[timer_value(timer_low, timer_high)],
        volume=volume,
        duty_cycle=control >> DUTY_CYCLE_SHIFT,
    )


def triangle_instruction(registers: Mapping[int, int], pitches: Mapping[int, int]) -> TriangleInstruction:
    """The instruction the triangle channel's registers sound.

    The channel states whether it sounds through the linear counter's reload value, so a full
    reload beside the control bit is the tick sounding and anything else is a rest.

    Args:
        registers: The whole register file at a tick.
        pitches: The pitch each timer value belongs to.

    Returns:
        TriangleInstruction: The frame the channel plays.

    Raises:
        KeyError: If the timer standing there belongs to no pitch the configuration covers.
    """
    linear_counter, timer_low, timer_high = channel_values(registers, GeneratorName.TRIANGLE)
    return TriangleInstruction(
        on=linear_counter == TRIANGLE_SOUNDING,
        pitch=pitches[timer_value(timer_low, timer_high)],
    )


def noise_instruction(registers: Mapping[int, int]) -> NoiseInstruction:
    """The instruction the noise channel's registers sound.

    The register counts periods from the fastest and the project counts them from the slowest, so
    the period reaches the instruction as its complement, the way the encoder wrote it.

    Args:
        registers: The whole register file at a tick.

    Returns:
        NoiseInstruction: The frame the channel plays.
    """
    control, period = channel_values(registers, GeneratorName.NOISE)
    volume = control & MAX_VOLUME
    return NoiseInstruction(
        on=volume > 0,
        period=MAX_PERIOD - (period & MAX_PERIOD),
        volume=volume,
        short=bool(period >> NOISE_MODE_SHIFT),
    )


def instructions_at(registers: Mapping[int, int], pitches: Mapping[int, int]) -> Dict[GeneratorName, InstructionUnion]:
    """Every channel's instruction for one tick, read back out of the registers standing at it.

    Args:
        registers: The whole register file at a tick.
        pitches: The pitch each timer value belongs to.

    Returns:
        Dict[GeneratorName, InstructionUnion]: One instruction per channel.
    """
    return {
        GeneratorName.PULSE1: pulse_instruction(registers, GeneratorName.PULSE1, pitches),
        GeneratorName.PULSE2: pulse_instruction(registers, GeneratorName.PULSE2, pitches),
        GeneratorName.TRIANGLE: triangle_instruction(registers, pitches),
        GeneratorName.NOISE: noise_instruction(registers),
    }


def instructions_from_trace(
    trace: RegisterTrace,
    timer_table: Mapping[int, int],
) -> Dict[GeneratorName, List[InstructionUnion]]:
    """The per-tick instructions a captured run plays, one stream per channel.

    This closes the loop the export opens: instructions became register values, the values became
    a file, the driver moved them to the APU, and reading them back states what the console sounds
    in the very terms the generators render from.

    Args:
        trace: The writes a run of the driver made.
        timer_table: The timer register value each pitch sounds at.

    Returns:
        Dict[GeneratorName, List[InstructionUnion]]: Each channel's stream, one instruction per
            tick the run sounded.
    """
    pitches = {timer: pitch for pitch, timer in timer_table.items()}
    streams: Dict[GeneratorName, List[InstructionUnion]] = {channel: [] for channel in GeneratorName.items()}

    for registers in register_file(trace):
        for channel, instruction in instructions_at(registers, pitches).items():
            streams[channel].append(instruction)

    return streams
