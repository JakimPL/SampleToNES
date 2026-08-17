from pydantic import BaseModel, Field


class Point(BaseModel, extra="forbid", frozen=True):
    """A position on the mark's design grid, in grid units."""

    x: float = Field(description="Distance from the left edge of the grid.")
    y: float = Field(description="Distance from the top edge of the grid.")


class CubicCurve(BaseModel, extra="forbid", frozen=True):
    """One cubic Bézier segment, starting where the segment before it ended."""

    control_start: Point = Field(description="Control point steering the segment away from its start.")
    control_end: Point = Field(description="Control point steering the segment into its end.")
    end: Point = Field(description="Point the segment reaches.")
