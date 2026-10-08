from typing import Final

import numpy as np
from PIL import Image

RGB_CHANNELS: Final[int] = 3
FULL_SCALE: Final[float] = 255.0
IMAGE_MODE: Final[str] = "RGB"


def to_image(pixels: np.ndarray) -> Image.Image:
    """The frame as an image: the red, green and blue fractions of every pixel rounded to eight bits.

    Args:
        pixels: The frame as DearPyGui hands it over, rows of red, green, blue and alpha fractions.
    """
    levels = np.clip(np.rint(pixels[:, :, :RGB_CHANNELS] * FULL_SCALE), 0, FULL_SCALE).astype(np.uint8)
    return Image.fromarray(levels, IMAGE_MODE)
