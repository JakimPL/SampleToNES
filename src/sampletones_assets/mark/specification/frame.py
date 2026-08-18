from typing import Self

from pydantic import BaseModel, Field, PositiveFloat, PositiveInt, model_validator


class MarkRim(BaseModel, extra="forbid", frozen=True):
    """The hairline drawn just inside the frame's edge, lifting it off a dark desktop."""

    inset: PositiveFloat = Field(description="Distance the hairline keeps from the frame's edge.")
    width: PositiveFloat = Field(description="Stroke width of the hairline.")
    opacity: float = Field(gt=0.0, le=1.0, description="Share of full opacity the hairline is drawn at.")


class MarkFrame(BaseModel, extra="forbid", frozen=True):
    """The rounded square the mark sits on.

    ``grid`` is the edge length every other coordinate is expressed in, so the whole design
    follows from this one number and scales to any icon size.
    """

    grid: PositiveInt = Field(description="Edge length of the design grid.")
    corner_radius: PositiveFloat = Field(description="Radius the frame's corners are rounded to.")
    rim: MarkRim = Field(description="The hairline inside the frame's edge.")

    @property
    def rim_radius(self) -> float:
        """Corner radius the rim follows, keeping it concentric with the frame."""
        return self.corner_radius - self.rim.inset

    @property
    def rim_extent(self) -> float:
        """Edge length of the rim's square, inset on both sides."""
        return self.grid - 2 * self.rim.inset

    @model_validator(mode="after")
    def _validate_rounding(self) -> Self:
        if 2 * self.corner_radius > self.grid:
            raise ValueError(f"The corner radius {self.corner_radius} must be at most half the grid {self.grid}")

        if self.rim.inset >= self.corner_radius:
            raise ValueError(f"The rim inset {self.rim.inset} must stay inside the corner radius {self.corner_radius}")

        return self
