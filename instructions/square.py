from typing import Optional

from pydantic import Field

from constants import MAX_PITCH, MIN_PITCH
from instructions.instruction import Instruction


class SquareInstruction(Instruction):
    pitch: Optional[int] = Field(..., ge=MIN_PITCH, le=MAX_PITCH, description="MIDI pitch (0-120)")
    volume: int = Field(..., ge=0, le=15, description="Volume (0-15)")
    duty_cycle: int = Field(..., ge=0, le=3, description="Duty cycle (e.g. 12, 25, 50, 75)")
