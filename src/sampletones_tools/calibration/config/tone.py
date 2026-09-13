from typing import Tuple

from pydantic import BaseModel, Field, PositiveFloat


class ToneConfig(BaseModel, frozen=True):
    """Steady sine probes covering the pitch range the criterion must track."""

    frequencies: Tuple[PositiveFloat, ...] = Field(
        min_length=1,
        description="Sine frequencies in Hz, one probe each.",
    )
