from typing import Optional

from pydantic import Field

from constants import MAX_PITCH, MIN_PITCH, PITCH_RANGE
from instructions.instruction import Instruction


class TriangleInstruction(Instruction):
    pitch: Optional[int] = Field(..., ge=MIN_PITCH, le=MAX_PITCH, description="MIDI pitch (0-120)")

    def distance(self, other: "TriangleInstruction") -> float:
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
