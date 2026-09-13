from pydantic import BaseModel, Field


class NoiseConfig(BaseModel, frozen=True):
    """Broadband noise probes: white noise and a low-passed random walk."""

    white_level: float = Field(
        gt=0.0,
        le=1.0,
        description="Standard deviation of the unit-scale white-noise probe.",
    )
