from typing import Callable

from sampletones_shared.constants.audio import UNITY_GAIN

GainReader = Callable[[], float]


def unity_gain() -> float:
    """The gain of a sound played at the level its audio holds."""
    return UNITY_GAIN
