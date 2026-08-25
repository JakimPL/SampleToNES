from __future__ import annotations

from typing import Dict, List, Tuple

from pydantic import Field

from sampletones_core.exporters.implementation.pulse import PulseExporter
from sampletones_core.instructions import PulseInstruction
from sampletones_player.registers.base import ChannelRegisters
from sampletones_player.registers.hold import hold
from sampletones_player.specification.registers import (
    DUTY_CYCLE_SHIFT,
    MAX_REGISTER_VALUE,
    MAX_TIMER_HIGH,
    SUSTAINED_LEVEL,
    TIMER_HIGH_SHIFT,
)


class PulseRegisters(ChannelRegisters):
    control: int = Field(..., ge=0, le=MAX_REGISTER_VALUE)
    timer_low: int = Field(..., ge=0, le=MAX_REGISTER_VALUE)
    timer_high: int = Field(..., ge=0, le=MAX_TIMER_HIGH)

    @property
    def values(self) -> Tuple[int, ...]:
        return (self.control, self.timer_low, self.timer_high)

    @classmethod
    def from_instructions(
        cls,
        instructions: List[PulseInstruction],
        timer_table: Dict[int, int],
    ) -> List[PulseRegisters]:
        """Turns a pulse channel's instructions into the registers each tick writes.

        Volume rides in the control byte's low nibble, so a rest keeps its pitch and duty cycle
        and sets the level to zero. Holding the period across a rest is what lets the driver leave
        the timer's high byte alone, and leaving it alone is what keeps the waveform's phase
        running the way a rendered channel does.

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
                cls(
                    control=(duty_cycle << DUTY_CYCLE_SHIFT) | SUSTAINED_LEVEL | volume,
                    timer_low=timer & MAX_REGISTER_VALUE,
                    timer_high=timer >> TIMER_HIGH_SHIFT,
                )
            )

        return registers
