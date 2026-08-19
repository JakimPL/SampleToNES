from pydantic import BaseModel, ConfigDict, Field

from sampletones_player.specification.clock import (
    FIXED_POINT_BITS,
    MAX_STEP_FRACTION,
    MAX_STEP_WHOLE,
)


class FixedPointStep(BaseModel):
    """The step the driver adds to its accumulator on every play call.

    The 6502 has no fractional arithmetic, so the step reaches the console as a whole byte and a
    16-bit fraction, and the song header carries the two fields as they are written here. Adding
    them into a 24-bit accumulator and reading the whole ticks off the top is what lets a stream
    of any rate advance by a fractional amount per call.

    Attributes:
        whole: The whole ticks every call advances by.
        fraction: The remainder, in 1/65536ths of a tick.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    whole: int = Field(..., ge=0, le=MAX_STEP_WHOLE)
    fraction: int = Field(..., ge=0, le=MAX_STEP_FRACTION)

    @property
    def value(self) -> int:
        """The step as one number, in the 1/65536ths of a tick the accumulator counts in."""
        return (self.whole << FIXED_POINT_BITS) | self.fraction
