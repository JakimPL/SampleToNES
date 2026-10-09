from typing import Tuple

from pydantic import BaseModel, Field, PositiveInt, field_validator


class MarkRender(BaseModel, extra="forbid", frozen=True):
    """How the mark is turned into pixels.

    Drawing happens at ``supersample`` times the design grid and the result is resampled
    down to each shipped size, which is what keeps the curve edges and the rounded corners
    smooth at 16 px.
    """

    supersample: PositiveInt = Field(description="Factor the design grid is drawn at before it is scaled down.")
    curve_samples: PositiveInt = Field(description="Points each cubic segment of the smooth half is stamped along.")
    raster_size: PositiveInt = Field(description="Edge length of the raster the application loads.")
    windows_sizes: Tuple[PositiveInt, ...] = Field(
        min_length=1,
        description="Edge lengths the multi-resolution Windows icon carries.",
    )

    @field_validator("windows_sizes")
    @classmethod
    def _validate_windows_sizes(cls, windows_sizes: Tuple[int, ...]) -> Tuple[int, ...]:
        if list(windows_sizes) != sorted(set(windows_sizes), reverse=True):
            raise ValueError("Windows icon sizes must be listed once each, in descending order")

        return windows_sizes
