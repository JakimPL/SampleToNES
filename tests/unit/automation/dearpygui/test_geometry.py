from typing import Final

import pytest

from automation.dearpygui.geometry import Rect

LEFT: Final[Rect] = Rect(x=10.0, y=20.0, width=30.0, height=40.0)
RIGHT: Final[Rect] = Rect(x=50.0, y=5.0, width=10.0, height=10.0)


class TestSpanning:
    def test_one_box_spans_itself(self) -> None:
        assert Rect.spanning([LEFT]) == LEFT

    def test_two_boxes_are_spanned_by_the_box_around_both(self) -> None:
        assert Rect.spanning([LEFT, RIGHT]) == Rect(x=10.0, y=5.0, width=50.0, height=55.0)

    def test_no_box_is_refused(self) -> None:
        with pytest.raises(ValueError):
            Rect.spanning([])


class TestFromOriginTo:
    def test_the_box_starts_at_the_corner_and_reaches_the_farthest_edges(self) -> None:
        assert Rect.from_origin_to([LEFT, RIGHT]) == Rect(x=0, y=0, width=60.0, height=60.0)

    def test_no_box_is_refused(self) -> None:
        with pytest.raises(ValueError):
            Rect.from_origin_to([])


class TestPixelBox:
    def test_the_margin_surrounds_the_box(self) -> None:
        assert LEFT.pixel_box(5, width=200, height=200) == (5, 15, 45, 65)

    def test_the_box_stays_inside_the_frame(self) -> None:
        assert LEFT.pixel_box(20, width=35, height=30) == (0, 0, 35, 30)
