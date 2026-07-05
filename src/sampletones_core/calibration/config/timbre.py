from typing import Annotated, Tuple

from pydantic import BaseModel, Field

DutyCycle = Annotated[float, Field(gt=0.0, lt=1.0)]


class TimbreConfig(BaseModel, frozen=True):
    """Pulse-wave probes distinguishing spectral shapes at a fixed pitch."""

    duty_cycles: Tuple[DutyCycle, ...] = Field(
        min_length=1,
        description="Pulse duty cycles, one probe each.",
    )
    frequency: float = Field(
        gt=0.0,
        description="Pulse frequency in Hz shared by every duty cycle.",
    )
