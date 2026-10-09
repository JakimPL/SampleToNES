from typing import Final

import pytest

from assets.pictures.boxes import corner_box, crop_box, union
from automation.dearpygui.geometry import Rect

LEFT: Final[Rect] = Rect(x=10.0, y=20.0, width=30.0, height=40.0)
RIGHT: Final[Rect] = Rect(x=50.0, y=5.0, width=10.0, height=10.0)


class TestUnion:
    def test_one_box_is_its_own_union(self) -> None:
        assert union([LEFT]) == LEFT

    def test_two_boxes_are_held_by_the_box_around_both(self) -> None:
        assert union([LEFT, RIGHT]) == Rect(x=10.0, y=5.0, width=50.0, height=55.0)

    def test_no_box_is_refused(self) -> None:
        with pytest.raises(ValueError):
            union([])


class TestCornerBox:
    def test_the_box_starts_at_the_corner_and_reaches_the_farthest_edges(self) -> None:
        assert corner_box([LEFT, RIGHT]) == Rect(x=0, y=0, width=60.0, height=60.0)

    def test_no_box_is_refused(self) -> None:
        with pytest.raises(ValueError):
            corner_box([])


class TestCropBox:
    def test_the_margin_surrounds_the_box(self) -> None:
        assert crop_box(LEFT, 5, width=200, height=200) == (5, 15, 45, 65)

    def test_the_box_stays_inside_the_frame(self) -> None:
        assert crop_box(LEFT, 20, width=35, height=30) == (0, 0, 35, 30)
