import numpy as np

from assets.stage.frames import eight_bit


class TestEightBit:
    def test_fractions_become_eight_bit_levels(self) -> None:
        pixels = np.array([[[1.0, 0.5, 0.0, 1.0]]], dtype=np.float32)

        assert eight_bit(pixels)[0, 0].tolist() == [255, 128, 0]

    def test_the_alpha_channel_is_left_behind(self) -> None:
        levels = eight_bit(np.zeros((2, 3, 4), dtype=np.float32))

        assert levels.shape == (2, 3, 3)
        assert levels.dtype == np.uint8
