from typing import Optional

from pydantic import Field

from constants import MAX_VOLUME
from instructions.instruction import Instruction


class NoiseInstruction(Instruction):
    period: Optional[int] = Field(..., ge=0, le=15, description="0-15, indexes into noise period table")
    volume: int = Field(..., ge=0, le=MAX_VOLUME, description="Volume (0-15)")
    mode: bool = Field(..., description="False = normal (15-bit), True = short mode (93-step)")
