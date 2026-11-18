from typing import Final

import numpy as np
import pytest

from assets.footage.composition import CompositionError, Layout, composed, placements

LAYOUT: Final[Layout] = Layout(width=100, height=200, top=20, bottom=160, gap=10)
GROUND: Final = (1, 2, 3)


class TestPlacements:
    def test_the_stack_is_centered_down_the_band_and_each_pane_across_the_frame(self) -> None:
        corners = placements([(60, 30), (80, 40)], LAYOUT)

        stack = 30 + LAYOUT.gap + 40
        top = LAYOUT.top + (LAYOUT.bottom - LAYOUT.top - stack) // 2
        assert corners == [(20, top), (10, top + 30 + LAYOUT.gap)]

    def test_a_pane_wider_than_the_frame_is_refused(self) -> None:
        with pytest.raises(CompositionError, match="wider"):
            placements([(LAYOUT.width + 1, 10)], LAYOUT)

    def test_a_stack_taller_than_the_band_is_refused(self) -> None:
        with pytest.raises(CompositionError, match="clear band"):
            placements([(10, 70), (10, 70)], LAYOUT)


class TestComposed:
    def test_each_pane_is_cut_from_the_screen_and_laid_on_the_ground(self) -> None:
        screen = np.arange(50 * 50 * 3, dtype=np.uint32).reshape(50, 50, 3).astype(np.uint8)
        box = (5, 10, 25, 40)

        frame = composed(screen, [box], LAYOUT, GROUND)

        ((x, y),) = placements([(20, 30)], LAYOUT)
        np.testing.assert_array_equal(frame[y : y + 30, x : x + 20], screen[10:40, 5:25])
        assert tuple(frame[0, 0]) == GROUND
        assert frame.shape == (LAYOUT.height, LAYOUT.width, 3)
