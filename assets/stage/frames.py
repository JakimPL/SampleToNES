import numpy as np

from automation.dearpygui.items.colors import COLOR_STEPS
from automation.frames import RGB_CHANNELS


def eight_bit(pixels: np.ndarray) -> np.ndarray:
    """The frame's red, green and blue fractions rounded to eight bits, rows of pixels of three levels each.

    Args:
        pixels: The frame as DearPyGui hands it over, rows of red, green, blue and alpha fractions.
    """
    return np.clip(np.rint(pixels[:, :, :RGB_CHANNELS] * COLOR_STEPS), 0, COLOR_STEPS).astype(np.uint8)
