from typing import Final, Tuple

import numpy as np
import pytest
from pydantic import ValidationError

from sampletones_player.specification.screen import MASTER_COLOR_COUNT
from sampletones_tools.player.graphics.picture.colors import MasterPalette
from tests.suite.base import BaseTestSuite

ROW_LENGTH: Final[int] = 16
GRAY: Final[str] = "#808080"
ORANGE: Final[str] = "#FF8000"
ORANGE_CHANNELS: Final[Tuple[int, int, int]] = (255, 128, 0)
ORANGE_INDEX: Final[int] = 17


def rows_of(colors: Tuple[str, ...]) -> Tuple[Tuple[str, ...], ...]:
    return tuple(colors[start : start + ROW_LENGTH] for start in range(0, len(colors), ROW_LENGTH))


def stated(count: int) -> Tuple[Tuple[str, ...], ...]:
    """``count`` gray colors with an orange one at a known number."""
    colors = [GRAY] * count
    colors[ORANGE_INDEX] = ORANGE
    return rows_of(tuple(colors))


class TestTheMasterPalette(BaseTestSuite):
    def test_every_color_becomes_one_row_of_the_array(self) -> None:
        array = MasterPalette(colors=stated(MASTER_COLOR_COUNT)).to_array()

        assert array.shape == (MASTER_COLOR_COUNT, 3)
        assert array.dtype == np.uint8

    def test_a_color_is_read_as_its_red_green_and_blue(self) -> None:
        array = MasterPalette(colors=stated(MASTER_COLOR_COUNT)).to_array()

        assert tuple(array[ORANGE_INDEX]) == ORANGE_CHANNELS

    def test_the_colors_keep_the_numbering_across_rows(self) -> None:
        array = MasterPalette(colors=stated(MASTER_COLOR_COUNT)).to_array()

        assert [index for index, color in enumerate(array) if tuple(color) == ORANGE_CHANNELS] == [ORANGE_INDEX]

    @pytest.mark.parametrize("count", (MASTER_COLOR_COUNT - 1, MASTER_COLOR_COUNT + 1))
    def test_a_palette_of_another_count_is_refused(self, count: int) -> None:
        with pytest.raises(ValidationError, match=str(MASTER_COLOR_COUNT)):
            MasterPalette(colors=stated(count))
