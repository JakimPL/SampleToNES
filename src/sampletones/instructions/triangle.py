from pydantic import Field

from sampletones.constants.general import MAX_PITCH, MIN_PITCH, PITCH_RANGE
from sampletones.utils import pitch_to_name

from .instruction import Instruction


class TriangleInstruction(Instruction):
    pitch: int = Field(..., ge=MIN_PITCH, le=MAX_PITCH, description="MIDI pitch (0-120)")

    @property
    def name(self) -> str:
        pitch = pitch_to_name(self.pitch)
        return f"T {pitch}"

    def __lt__(self, other: "TriangleInstruction") -> bool:
        if not isinstance(other, TriangleInstruction):
            return TypeError("Cannot compare TriangleInstruction with different type")
        return self.pitch < other.pitch

    def distance(self, other: Instruction) -> float:
        if not isinstance(other, TriangleInstruction):
            raise TypeError("Cannot compute distance between different instruction types")

        both_silent = not self.on and not other.on
        one_silent = (not self.on) != (not other.on)

        if both_silent:
            return 0.0
        elif one_silent:
            return 0.5
        else:
            pitch1 = self.pitch
            pitch2 = other.pitch
            pitch_difference = abs(pitch1 - pitch2) / PITCH_RANGE

        return pitch_difference
