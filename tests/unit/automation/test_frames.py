from typing import Final

import numpy as np
import pytest

from automation.dearpygui.geometry import Rect
from automation.frames import NothingChangedError, changed_box

FRAME: Final[tuple[int, int]] = (100, 80)


def frame(width: int, height: int) -> np.ndarray:
    return np.zeros((height, width, 4), dtype=np.float32)


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
