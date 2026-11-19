from typing import Final

import numpy as np
import pytest

from assets.footage.composition import CompositionError, Layout, Placement, composed, enlargement, placements

LAYOUT: Final[Layout] = Layout(width=100, height=200, top=20, bottom=160, gap=10)
GROUND: Final = (1, 2, 3)


class TestPlacements:
    def test_the_stack_grows_until_it_fills_the_clear_band(self) -> None:
        laid = placements([(40, 30), (40, 40)], LAYOUT)

        stack = laid[-1].y + laid[-1].height - laid[0].y
        assert LAYOUT.bottom - LAYOUT.top - len(laid) <= stack <= LAYOUT.bottom - LAYOUT.top
        assert laid[1].y - (laid[0].y + laid[0].height) == LAYOUT.gap

    def test_a_wide_stack_grows_until_it_fills_the_frame_between_its_side_gaps(self) -> None:
        assert placements([(40, 10)], LAYOUT) == [Placement(x=10, y=LAYOUT.top + (140 - 20) // 2, width=80, height=20)]

    def test_each_pane_is_centered_across_the_frame(self) -> None:
        laid = placements([(40, 10), (20, 10)], LAYOUT)

        assert [placement.x for placement in laid] == [(LAYOUT.width - placement.width) // 2 for placement in laid]

    def test_a_pane_wider_than_the_frame_is_refused(self) -> None:
        with pytest.raises(CompositionError, match="wider"):
            enlargement([(LAYOUT.width - 2 * LAYOUT.gap + 1, 10)], LAYOUT)

    def test_a_stack_taller_than_the_band_is_refused(self) -> None:
        with pytest.raises(CompositionError, match="clear band"):
            enlargement([(10, 70), (10, 70)], LAYOUT)


class TestComposed:
    SCREEN: Final[np.ndarray] = np.arange(50 * 50 * 3, dtype=np.uint32).reshape(50, 50, 3).astype(np.uint8)
    BOX: Final = (5, 10, 25, 40)

    def test_a_pane_that_fits_exactly_is_laid_as_the_screen_drew_it(self) -> None:
        layout = Layout(width=20, height=60, top=10, bottom=40, gap=0)

        frame = composed(self.SCREEN, [self.BOX], layout, GROUND)

        np.testing.assert_array_equal(frame[10:40], self.SCREEN[10:40, 5:25])
        assert tuple(frame[0, 0]) == GROUND

    def test_an_enlarged_pane_is_laid_on_the_ground(self) -> None:
        frame = composed(self.SCREEN, [self.BOX], LAYOUT, GROUND)

        (placement,) = placements([(20, 30)], LAYOUT)
        assert frame.shape == (LAYOUT.height, LAYOUT.width, 3)
        assert tuple(frame[0, 0]) == GROUND
        assert tuple(frame[placement.y - 1, placement.x + 1]) == GROUND
        assert tuple(frame[placement.y, placement.x + 1]) != GROUND
