from abc import ABC, abstractmethod
from typing import Dict, List, Tuple

from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.constants.general import MAX_PERIOD
from sampletones_core.exporters.implementation.noise import NoiseExporter
from sampletones_core.exporters.implementation.pulse import PulseExporter
from sampletones_core.exporters.implementation.triangle import TriangleExporter
from sampletones_core.instructions import (
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)

from .specification.registers import (
    DUTY_CYCLE_SHIFT,
    MAX_REGISTER_VALUE,
    MAX_TIMER_HIGH,
    NOISE_MODE_SHIFT,
    SUSTAINED_LEVEL,
    TIMER_HIGH_SHIFT,
    TRIANGLE_COUNTER_CONTROL,
    TRIANGLE_SILENT_RELOAD,
    TRIANGLE_SOUNDING_RELOAD,
)


class ChannelRegisters(BaseModel, ABC):
    """The register values one channel writes for a single engine tick.

    The driver interprets nothing: it moves these bytes to the addresses its channel owns.
    Every rule the hardware follows — how a duty cycle reaches its bits, which value silences
    a channel, how a pitch becomes a period — is settled here, where it is testable.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    @property
    @abstractmethod
    def values(self) -> Tuple[int, ...]:
        """The tick's register values, in the order the driver writes them.

        Returns:
            Tuple[int, ...]: One value per register the channel writes each tick.
        """


class PulseRegisters(ChannelRegisters):
    control: int = Field(..., ge=0, le=MAX_REGISTER_VALUE)
    timer_low: int = Field(..., ge=0, le=MAX_REGISTER_VALUE)
    timer_high: int = Field(..., ge=0, le=MAX_TIMER_HIGH)

    @property
    def values(self) -> Tuple[int, ...]:
        return (self.control, self.timer_low, self.timer_high)


class TriangleRegisters(ChannelRegisters):
    linear_counter: int = Field(..., ge=0, le=MAX_REGISTER_VALUE)
    timer_low: int = Field(..., ge=0, le=MAX_REGISTER_VALUE)
    timer_high: int = Field(..., ge=0, le=MAX_TIMER_HIGH)

    @property
    def values(self) -> Tuple[int, ...]:
        return (self.linear_counter, self.timer_low, self.timer_high)


class NoiseRegisters(ChannelRegisters):
    control: int = Field(..., ge=0, le=MAX_REGISTER_VALUE)
    period: int = Field(..., ge=0, le=MAX_REGISTER_VALUE)

    @property
    def values(self) -> Tuple[int, ...]:
        return (self.control, self.period)


def hold(values: List[int], index: int) -> int:
    """Reads a held stream at a tick, sustaining its final value over the release tick.

    An exporter states a channel's pitch and timbre for every tick its instructions cover, and
    appends one silent tick past them so a sample ends quiet. That release tick reads the values
    the channel was holding when it stopped sounding.

    Args:
        values: The held stream, covering at least one tick.
        index: The tick to read.

    Returns:
        int: The value at that tick, or the stream's final value once the index reaches its end.
    """
    return values[min(index, len(values) - 1)]


def encode_pulse(
    instructions: List[PulseInstruction],
    timer_table: Dict[int, int],
) -> List[PulseRegisters]:
    """Turns a pulse channel's instructions into the registers each tick writes.

    Volume rides in the control byte's low nibble, so a rest keeps its pitch and duty cycle and
    sets the level to zero. Holding the period across a rest is what lets the driver leave the
    timer's high byte alone, and leaving it alone is what keeps the waveform's phase running the
    way a rendered channel does.

    Args:
        instructions: The channel's per-tick instructions.
        timer_table: The timer register value each pitch sounds at.

    Returns:
        List[PulseRegisters]: One register set per tick, including the closing release tick.
    """
    _, pitches, volumes, duty_cycles = PulseExporter.extract_data(instructions)

    registers: List[PulseRegisters] = []
    for index, volume in enumerate(volumes):
        timer = timer_table[hold(pitches, index)]
        duty_cycle = hold(duty_cycles, index)
        registers.append(
            PulseRegisters(
                control=(duty_cycle << DUTY_CYCLE_SHIFT) | SUSTAINED_LEVEL | volume,
                timer_low=timer & MAX_REGISTER_VALUE,
                timer_high=timer >> TIMER_HIGH_SHIFT,
            )
        )

    return registers


def encode_triangle(
    instructions: List[TriangleInstruction],
    timer_table: Dict[int, int],
) -> List[TriangleRegisters]:
    """Turns a triangle channel's instructions into the registers each tick writes.

    The triangle sounds at one level, so a tick states whether it sounds through the linear
    counter's reload value: a full reload keeps the waveform running, and a reload of zero
    holds it silent. The control bit stays set throughout, which is what makes the counter
    reload every frame and the note last as long as the ticks do.

    The timer is written from the instruction's pitch directly, and the channel sounds an
    octave below it — the same octave a rendered triangle sounds.

    Args:
        instructions: The channel's per-tick instructions.
        timer_table: The timer register value each pitch sounds at.

    Returns:
        List[TriangleRegisters]: One register set per tick, including the closing release tick.
    """
    _, pitches, volumes = TriangleExporter.extract_data(instructions)

    registers: List[TriangleRegisters] = []
    for index, volume in enumerate(volumes):
        timer = timer_table[hold(pitches, index)]
        reload_value = TRIANGLE_SOUNDING_RELOAD if volume > 0 else TRIANGLE_SILENT_RELOAD
        registers.append(
            TriangleRegisters(
                linear_counter=TRIANGLE_COUNTER_CONTROL | reload_value,
                timer_low=timer & MAX_REGISTER_VALUE,
                timer_high=timer >> TIMER_HIGH_SHIFT,
            )
        )

    return registers


def encode_noise(instructions: List[NoiseInstruction]) -> List[NoiseRegisters]:
    """Turns a noise channel's instructions into the registers each tick writes.

    The project counts noise periods from the slowest, and the register counts them from the
    fastest, so a period reaches the register as its complement. The mode bit rides above it,
    selecting the shift register's short 93-step cycle.

    Args:
        instructions: The channel's per-tick instructions.

    Returns:
        List[NoiseRegisters]: One register set per tick, including the closing release tick.
    """
    _, periods, volumes, modes = NoiseExporter.extract_data(instructions)

    registers: List[NoiseRegisters] = []
    for index, volume in enumerate(volumes):
        period = hold(periods, index)
        mode = hold(modes, index)
        registers.append(
            NoiseRegisters(
                control=SUSTAINED_LEVEL | volume,
                period=(mode << NOISE_MODE_SHIFT) | (MAX_PERIOD - period),
            )
        )

    return registers
