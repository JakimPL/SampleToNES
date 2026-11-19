from __future__ import annotations

from pydantic import Field

from sampletones_core.constants.enums import InstructionClassName
from sampletones_core.constants.general import (
    MAX_PERIOD,
    MAX_VOLUME,
    NOISE_PERIODS,
)

from ..instruction import Instruction


class NoiseInstruction(Instruction):
    period: int = Field(..., ge=0, le=MAX_PERIOD, description="Index into the noise period table")
    volume: int = Field(..., ge=0, le=MAX_VOLUME, description="Volume (0-15)")
    short: bool = Field(..., description="False = normal (15-bit), True = short mode (93-step)")

    @property
    def name(self) -> str:
        period = f"p{NOISE_PERIODS[self.period]}"
        volume = f"v{self.volume:X}"
        short = "s" if self.short else "l"
        return f"N {period} {volume} {short}"

    def __lt__(self, other: Instruction) -> bool:
        if not isinstance(other, NoiseInstruction):
            raise TypeError("Cannot compare NoiseInstruction with different type")

        return (NOISE_PERIODS[self.period], -self.volume, self.short) < (
            NOISE_PERIODS[other.period],
            -other.volume,
            other.short,
        )

    @classmethod
    def null_instruction(cls) -> NoiseInstruction:
        return NoiseInstruction(
            on=False,
            period=0,
            volume=0,
            short=False,
        )

    @classmethod
    def default_instruction(cls) -> NoiseInstruction:
        return NoiseInstruction(
            on=True,
            period=0,
            volume=MAX_VOLUME,
            short=False,
        )

    @classmethod
    def class_name(cls) -> InstructionClassName:
        return InstructionClassName.NOISE_INSTRUCTION
