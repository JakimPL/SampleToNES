from typing import Final

import numpy as np
from PIL import Image

from assets.pictures.jitter import block_counts, is_jitter

SIZE: Final[tuple[int, int]] = (200, 100)


def picture() -> Image.Image:
    return Image.new("RGB", SIZE, (40, 40, 60))


def with_pixels(image: Image.Image, pixels: list[tuple[int, int]]) -> Image.Image:
    changed = image.copy()
    for x, y in pixels:
        changed.putpixel((x, y), (200, 200, 200))
    return changed


class TestIsJitter:
    def test_the_same_drawing_is_jitter(self) -> None:
        assert is_jitter(picture(), picture())

    def test_scattered_single_columns_on_edges_are_jitter(self) -> None:
        drawn = with_pixels(picture(), [(10, y) for y in range(20, 31)] + [(150, 60), (150, 61), (151, 61)])

        assert is_jitter(picture(), drawn)

    def test_a_block_of_changed_pixels_is_a_change(self) -> None:
        drawn = with_pixels(picture(), [(x, y) for x in range(50, 54) for y in range(50, 54)])

        assert not is_jitter(picture(), drawn)

    def test_a_scatter_covering_much_of_the_frame_is_a_change(self) -> None:
        drawn = with_pixels(picture(), [(x, y) for x in range(0, 200, 4) for y in range(0, 100, 4)])

        assert not is_jitter(picture(), drawn)

    def test_a_drawing_of_another_size_is_a_change(self) -> None:
        assert not is_jitter(picture(), Image.new("RGB", (SIZE[0] + 1, SIZE[1]), (40, 40, 60)))


class TestBlockCounts:
    def test_a_lone_pixel_counts_once_in_every_block_around_it(self) -> None:
        changed = np.zeros((5, 5), dtype=bool)
        changed[2, 2] = True

        counts = block_counts(changed)

        assert counts[2, 2] == 1
        assert counts[1:4, 1:4].sum() == 9
        assert counts[0, 0] == 0

    def test_a_column_of_three_counts_three_at_its_middle(self) -> None:
        changed = np.zeros((5, 5), dtype=bool)
        changed[1:4, 2] = True

        assert block_counts(changed)[2, 2] == 3
