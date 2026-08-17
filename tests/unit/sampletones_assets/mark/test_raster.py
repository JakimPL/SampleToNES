from typing import Final, Tuple

import pytest

from sampletones_assets.mark.raster import MarkRaster
from sampletones_assets.mark.specification import Mark
from sampletones_shared.utils.color import parse_hex_color

CORNER: Final[Tuple[int, int]] = (0, 0)
ALPHA: Final[int] = 3
CHANNELS: Final[int] = 3


@pytest.fixture(name="mark", scope="module")
def mark_fixture() -> Mark:
    return Mark.load()


class TestMarkRaster:
    def test_the_image_covers_the_supersampled_grid(self, mark: Mark) -> None:
        image = MarkRaster(mark).render()
        edge = mark.frame.grid * mark.render.supersample
        assert image.size == (edge, edge)

    def test_the_image_corner_stays_clear_of_the_rounded_frame(self, mark: Mark) -> None:
        image = MarkRaster(mark).render()
        assert image.getpixel(CORNER)[ALPHA] == 0

    def test_the_frame_centre_carries_the_background(self, mark: Mark) -> None:
        """The frame reaches the top edge between its rounded corners, so the ground there is opaque."""
        image = MarkRaster(mark).render()
        centre = image.size[0] // 2
        assert image.getpixel((centre, 1))[ALPHA] == 255

    def test_the_smooth_half_is_drawn_in_its_own_colour(self, mark: Mark) -> None:
        image = MarkRaster(mark).render()
        scale = mark.render.supersample
        start = mark.waves.sine.start
        pixel = image.getpixel((round(start.x * scale), round(start.y * scale)))
        assert pixel[:CHANNELS] == parse_hex_color(mark.colors.sine)[:CHANNELS]

    def test_the_stepped_half_is_drawn_in_its_own_colour(self, mark: Mark) -> None:
        image = MarkRaster(mark).render()
        scale = mark.render.supersample
        corner = mark.waves.square.points[1]
        pixel = image.getpixel((round(corner.x * scale), round(corner.y * scale)))
        assert pixel[:CHANNELS] == parse_hex_color(mark.colors.square)[:CHANNELS]
