from __future__ import annotations

from sampletones_core.constants.enums import InstructionClassName
from sampletones_core.constants.general import MIN_PITCH
from sampletones_core.utils.frequencies import pitch_to_name

from ..instruction import Instruction
from ..tonal import TonalInstruction


class TriangleInstruction(TonalInstruction):
    @property
    def name(self) -> str:
        pitch = pitch_to_name(self.pitch)
        return f"T {pitch}"

    def __lt__(self, other: Instruction) -> bool:
        if not isinstance(other, TriangleInstruction):
            raise TypeError("Cannot compare TriangleInstruction with different type")

        return self.pitch < other.pitch

    @classmethod
    def null_instruction(cls) -> TriangleInstruction:
        return TriangleInstruction(
            on=False,
            pitch=MIN_PITCH,
        )

    @classmethod
    def default_instruction(cls) -> TriangleInstruction:
        return TriangleInstruction(
            on=True,
            pitch=MIN_PITCH,
        )

    @classmethod
    def class_name(cls) -> InstructionClassName:
        return InstructionClassName.TRIANGLE_INSTRUCTION
