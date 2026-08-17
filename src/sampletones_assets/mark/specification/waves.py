import itertools
from typing import Self, Tuple

from pydantic import BaseModel, Field, PositiveFloat, model_validator

from sampletones_assets.mark.specification.point import CubicCurve, Point


class MarkSine(BaseModel, extra="forbid", frozen=True):
    """The smooth half of the wave, as cubic segments running on from the start point."""

    start: Point = Field(description="Point the wave enters the frame at.")
    curves: Tuple[CubicCurve, ...] = Field(min_length=1, description="Segments the wave follows, in drawing order.")

    @property
    def end(self) -> Point:
        """Point the last segment reaches, where the stepped half takes over."""
        return self.curves[-1].end


class MarkSquare(BaseModel, extra="forbid", frozen=True):
    """The stepped half of the wave, as corners joined by axis-aligned segments."""

    points: Tuple[Point, ...] = Field(min_length=2, description="Corners the wave turns at, in drawing order.")

    @model_validator(mode="after")
    def _validate_segments_run_along_one_axis(self) -> Self:
        for start, end in itertools.pairwise(self.points):
            if start.x != end.x and start.y != end.y:
                raise ValueError(
                    f"A square wave segment runs along one axis, "
                    f"where ({start.x}, {start.y}) to ({end.x}, {end.y}) turns on both"
                )

        return self


class MarkWaves(BaseModel, extra="forbid", frozen=True):
    """The single wave the mark carries: one sample entering smooth and leaving stepped.

    Both halves are stroked at the same width, which is what reads them as one continuous
    wave crossing the frame.
    """

    width: PositiveFloat = Field(description="Stroke width both halves of the wave are drawn at.")
    sine: MarkSine = Field(description="The smooth half, entering from the left.")
    square: MarkSquare = Field(description="The stepped half, leaving to the right.")

    @model_validator(mode="after")
    def _validate_the_halves_meet(self) -> Self:
        handover = self.square.points[0]
        if handover != self.sine.end:
            raise ValueError(
                f"The stepped half starts where the smooth half ends, "
                f"where it starts at ({handover.x}, {handover.y}) "
                f"and the smooth half ends at ({self.sine.end.x}, {self.sine.end.y})"
            )

        return self
