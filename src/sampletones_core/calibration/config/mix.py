from typing import Tuple

from pydantic import BaseModel, Field, PositiveFloat


class MixConfig(BaseModel, frozen=True):
    """Tone-plus-noise probes grading how noise masks a steady reference tone."""

    noise_levels: Tuple[PositiveFloat, ...] = Field(
        min_length=1,
        description="Noise standard deviations relative to the unit reference tone, one probe each.",
    )
