from pydantic import BaseModel, Field


class DynamicsConfig(BaseModel, frozen=True):
    """A level probe beside the crescendo: a loud white-noise burst dropping straight to a quiet hiss."""

    burst_seconds: float = Field(
        gt=0.0,
        description="Duration of the burst at the white noise level, in seconds.",
    )
    hiss_level: float = Field(
        gt=0.0,
        lt=1.0,
        description="Level of the hiss following the burst, against the burst.",
    )
