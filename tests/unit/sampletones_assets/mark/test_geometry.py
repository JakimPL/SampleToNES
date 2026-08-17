import itertools
from typing import Final

import pytest

from sampletones_assets.mark.geometry import Rectangle, sine_points, square_rectangles
from sampletones_assets.mark.specification import Mark

SAMPLES: Final[int] = 5


def _overlap(first: Rectangle, second: Rectangle) -> float:
    width = min(first.right, second.right) - max(first.left, second.left)
    height = min(first.bottom, second.bottom) - max(first.top, second.top)
    return min(width, height)


class TestSinePoints:
    def test_the_polyline_runs_from_the_start_to_the_handover(self) -> None:
        sine = Mark.load().waves.sine
        points = sine_points(sine, SAMPLES)

        assert points[0] == sine.start
        assert points[-1].x == pytest.approx(sine.end.x)
        assert points[-1].y == pytest.approx(sine.end.y)

    def test_every_segment_contributes_its_samples(self) -> None:
        sine = Mark.load().waves.sine
        assert len(sine_points(sine, SAMPLES)) == len(sine.curves) * SAMPLES + 1

    def test_the_polyline_stays_within_the_curve_the_definition_draws(self) -> None:
        """The wave swings between the extremes its control points reach, keeping it inside the frame."""
        sine = Mark.load().waves.sine
        controls = [sine.start] + [
            point for curve in sine.curves for point in (curve.control_start, curve.control_end, curve.end)
        ]
        lowest = min(point.y for point in controls)
        highest = max(point.y for point in controls)

        for point in sine_points(sine, SAMPLES):
            assert lowest <= point.y <= highest


class TestSquareRectangles:
    def test_one_rectangle_covers_each_segment(self) -> None:
        square = Mark.load().waves.square
        assert len(square_rectangles(square, width=4.0)) == len(square.points) - 1

    def test_every_rectangle_reads_left_to_right_and_top_to_bottom(self) -> None:
        square = Mark.load().waves.square
        for rectangle in square_rectangles(square, width=4.0):
            assert rectangle.left < rectangle.right
            assert rectangle.top < rectangle.bottom

    def test_a_segment_carries_the_stroke_width_across_its_run(self) -> None:
        width = 4.0
        square = Mark.load().waves.square
        for (start, end), rectangle in zip(
            itertools.pairwise(square.points),
            square_rectangles(square, width=width),
        ):
            across = rectangle.bottom - rectangle.top if start.y == end.y else rectangle.right - rectangle.left
            assert across == pytest.approx(width)

    def test_consecutive_rectangles_meet_at_the_corner_they_turn_on(self) -> None:
        """Overlapping rectangles fill the right-angle miter, so the stepped half draws as one stroke."""
        square = Mark.load().waves.square
        for first, second in itertools.pairwise(square_rectangles(square, width=4.0)):
            assert _overlap(first, second) > 0.0
