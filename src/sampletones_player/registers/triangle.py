from __future__ import annotations

from typing import Dict, List, Tuple

from pydantic import Field

from sampletones_core.exporters.implementation.triangle import TriangleExporter
from sampletones_core.instructions import TriangleInstruction
from sampletones_player.registers.base import ChannelRegisters
from sampletones_player.registers.hold import hold
from sampletones_player.specification.registers import (
    MAX_REGISTER_VALUE,
    MAX_TIMER_HIGH,
    TIMER_HIGH_SHIFT,
    TRIANGLE_COUNTER_CONTROL,
    TRIANGLE_SILENT_RELOAD,
    TRIANGLE_SOUNDING_RELOAD,
)


class TriangleRegisters(ChannelRegisters):
    linear_counter: int = Field(..., ge=0, le=MAX_REGISTER_VALUE)
    timer_low: int = Field(..., ge=0, le=MAX_REGISTER_VALUE)
    timer_high: int = Field(..., ge=0, le=MAX_TIMER_HIGH)

    @property
    def values(self) -> Tuple[int, ...]:
        return (self.linear_counter, self.timer_low, self.timer_high)

    @classmethod
    def from_instructions(
        cls,
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
                cls(
                    linear_counter=TRIANGLE_COUNTER_CONTROL | reload_value,
                    timer_low=timer & MAX_REGISTER_VALUE,
                    timer_high=timer >> TIMER_HIGH_SHIFT,
                )
            )

        return registers
