from __future__ import annotations

from typing import List, Tuple

from pydantic import Field

from sampletones_core.constants.general import MAX_PERIOD
from sampletones_core.exporters.implementation.noise import NoiseExporter
from sampletones_core.instructions import NoiseInstruction
from sampletones_player.registers.base import ChannelRegisters
from sampletones_player.registers.hold import hold
from sampletones_player.specification.registers import (
    MAX_REGISTER_VALUE,
    NOISE_MODE_SHIFT,
    SUSTAINED_LEVEL,
)


class NoiseRegisters(ChannelRegisters):
    control: int = Field(..., ge=0, le=MAX_REGISTER_VALUE)
    period: int = Field(..., ge=0, le=MAX_REGISTER_VALUE)

    @property
    def values(self) -> Tuple[int, ...]:
        return (self.control, self.period)

    @classmethod
    def from_instructions(cls, instructions: List[NoiseInstruction]) -> List[NoiseRegisters]:
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
                cls(
                    control=SUSTAINED_LEVEL | volume,
                    period=(mode << NOISE_MODE_SHIFT) | (MAX_PERIOD - period),
                )
            )

        return registers
