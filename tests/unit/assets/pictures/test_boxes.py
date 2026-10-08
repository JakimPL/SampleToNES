from typing import Final

import numpy as np
import pytest

from assets.pictures.boxes import NothingChangedError, changed_box, crop_box, union
from automation.dearpygui.geometry import Rect

LEFT: Final[Rect] = Rect(x=10.0, y=20.0, width=30.0, height=40.0)
RIGHT: Final[Rect] = Rect(x=50.0, y=5.0, width=10.0, height=10.0)
FRAME: Final[tuple[int, int]] = (100, 80)


def frame(width: int, height: int) -> np.ndarray:
    return np.zeros((height, width, 4), dtype=np.float32)


class TestUnion:
    def test_one_box_is_its_own_union(self) -> None:
        assert union([LEFT]) == LEFT

    def test_two_boxes_are_held_by_the_box_around_both(self) -> None:
        assert union([LEFT, RIGHT]) == Rect(x=10.0, y=5.0, width=50.0, height=55.0)

    def test_no_box_is_refused(self) -> None:
        with pytest.raises(ValueError):
            union([])


class TestCropBox:
    def test_the_margin_surrounds_the_box(self) -> None:
        assert crop_box(LEFT, 5, width=200, height=200) == (5, 15, 45, 65)

    def test_the_box_stays_inside_the_frame(self) -> None:
        assert crop_box(LEFT, 20, width=35, height=30) == (0, 0, 35, 30)


class TestChangedBox:
    def test_the_box_surrounds_every_changed_pixel(self) -> None:
        before = frame(*FRAME)
        after = before.copy()
        after[10, 20, 0] = 1.0
        after[30, 60, 2] = 1.0

        assert changed_box(before, after) == Rect(x=20.0, y=10.0, width=41.0, height=21.0)

    def test_a_change_within_the_tolerance_is_no_change(self) -> None:
        before = frame(*FRAME)
        after = before.copy()
        after[10, 20, 1] = 1.0 / 255.0

        with pytest.raises(NothingChangedError):
            changed_box(before, after)

    def test_alpha_alone_is_no_change(self) -> None:
        before = frame(*FRAME)
        after = before.copy()
        after[:, :, 3] = 1.0

        with pytest.raises(NothingChangedError):
            changed_box(before, after)
