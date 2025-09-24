from typing import Optional

from pydantic import Field

from constants import MAX_PITCH, MIN_PITCH
from instructions.instruction import Instruction


class TriangleInstruction(Instruction):
    pitch: Optional[int] = Field(..., ge=MIN_PITCH, le=MAX_PITCH, description="MIDI pitch (0-120)")
