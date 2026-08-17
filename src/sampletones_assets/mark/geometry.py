import itertools
from dataclasses import dataclass
from typing import List

from sampletones_assets.mark.specification.point import CubicCurve, Point
from sampletones_assets.mark.specification.waves import MarkSine, MarkSquare


@dataclass(frozen=True)
class Rectangle:
    """An axis-aligned box in grid units, the shape one segment of the stepped half fills."""

    left: float
    top: float
    right: float
    bottom: float


def _cubic_coordinate(
    start: float,
    control_start: float,
    control_end: float,
    end: float,
    progress: float,
) -> float:
    remainder = 1.0 - progress
    return (
        remainder**3 * start
        + 3 * remainder**2 * progress * control_start
        + 3 * remainder * progress**2 * control_end
        + progress**3 * end
    )


def _cubic_point(
    start: Point,
    curve: CubicCurve,
    progress: float,
) -> Point:
    return Point(
        x=_cubic_coordinate(start.x, curve.control_start.x, curve.control_end.x, curve.end.x, progress),
        y=_cubic_coordinate(start.y, curve.control_start.y, curve.control_end.y, curve.end.y, progress),
    )


def sine_points(sine: MarkSine, samples: int) -> List[Point]:
    """The smooth half as a polyline, sampled evenly along every segment.

    Each segment contributes ``samples`` points, ending on its own end point, so the next
    segment starts where the previous one arrived and the polyline runs unbroken from the
    wave's start to its handover.
    """
    points = [sine.start]
    position = sine.start
    for curve in sine.curves:
        for step in range(1, samples + 1):
            points.append(_cubic_point(position, curve, step / samples))

        position = curve.end

    return points


def _direction(delta: float) -> float:
    if delta > 0:
        return 1.0

    if delta < 0:
        return -1.0

    return 0.0


def _segment_rectangle(
    start: Point,
    end: Point,
    *,
    half_width: float,
    joined_start: bool,
    joined_end: bool,
) -> Rectangle:
    """The stroke rectangle of one axis-aligned segment.

    A joined end reaches half the stroke width past its corner, so consecutive rectangles
    fill their right-angle miter; an open end keeps a butt cap.
    """
    direction_x = _direction(end.x - start.x)
    direction_y = _direction(end.y - start.y)
    start_reach = half_width if joined_start else 0.0
    end_reach = half_width if joined_end else 0.0

    reached_start = (
        start.x - direction_x * start_reach,
        start.y - direction_y * start_reach,
    )
    reached_end = (
        end.x + direction_x * end_reach,
        end.y + direction_y * end_reach,
    )
    across_x = half_width * abs(direction_y)
    across_y = half_width * abs(direction_x)

    return Rectangle(
        left=min(reached_start[0], reached_end[0]) - across_x,
        top=min(reached_start[1], reached_end[1]) - across_y,
        right=max(reached_start[0], reached_end[0]) + across_x,
        bottom=max(reached_start[1], reached_end[1]) + across_y,
    )


def square_rectangles(square: MarkSquare, width: float) -> List[Rectangle]:
    """The stepped half as filled rectangles, one per segment between its corners.

    The rectangles meet at every corner the wave turns at, so the sequence covers the
    stroke a vector renderer draws with square joins.
    """
    segments = list(itertools.pairwise(square.points))
    final_segment = len(segments) - 1
    return [
        _segment_rectangle(
            start,
            end,
            half_width=width / 2,
            joined_start=index > 0,
            joined_end=index < final_segment,
        )
        for index, (start, end) in enumerate(segments)
    ]
