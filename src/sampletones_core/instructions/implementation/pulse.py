from __future__ import annotations

from pydantic import Field

from sampletones_core.constants.enums import InstructionClassName
from sampletones_core.constants.general import (
    DUTY_CYCLES,
    MAX_DUTY_CYCLE,
    MAX_VOLUME,
    MIN_PITCH,
)
from sampletones_core.utils.frequencies import pitch_to_name

from ..instruction import Instruction
from ..tonal import TonalInstruction


class PulseInstruction(TonalInstruction):
    volume: int = Field(..., ge=0, le=MAX_VOLUME, description="Volume (0-15)")
    duty_cycle: int = Field(
        ...,
        ge=0,
        le=MAX_DUTY_CYCLE,
        description="Duty cycle (e.g. 12, 25, 50, 75)",
    )

    @property
    def name(self) -> str:
        pitch = pitch_to_name(self.pitch)
        volume = f"v{self.volume:X}"
        duty = f"D{DUTY_CYCLES[self.duty_cycle]*100:.0f}"
        return f"P {pitch} {volume} {duty}"

    def __lt__(self, other: Instruction) -> bool:
        if not isinstance(other, PulseInstruction):
            raise TypeError("Cannot compare PulseInstruction with different type")

        return (self.pitch, -self.volume, self.duty_cycle) < (
            other.pitch,
            -other.volume,
            other.duty_cycle,
        )

    @classmethod
    def null_instruction(cls) -> PulseInstruction:
        return PulseInstruction(
            on=False,
            pitch=MIN_PITCH,
            volume=0,
            duty_cycle=0,
        )

    @classmethod
    def default_instruction(cls) -> PulseInstruction:
        return PulseInstruction(
            on=True,
            pitch=MIN_PITCH,
            volume=MAX_VOLUME,
            duty_cycle=0,
        )

    @classmethod
    def class_name(cls) -> InstructionClassName:
        return InstructionClassName.PULSE_INSTRUCTION
