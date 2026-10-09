import numpy as np

from assets.pictures.frames import to_image


class TestToImage:
    def test_fractions_become_eight_bit_levels(self) -> None:
        pixels = np.array([[[1.0, 0.5, 0.0, 1.0]]], dtype=np.float32)

        assert to_image(pixels).getpixel((0, 0)) == (255, 128, 0)

    def test_the_alpha_channel_is_left_behind(self) -> None:
        pixels = np.zeros((2, 3, 4), dtype=np.float32)
        image = to_image(pixels)

        assert image.mode == "RGB"
        assert image.size == (3, 2)
