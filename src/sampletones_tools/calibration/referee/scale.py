from typing import Final

from sampletones_core.reconstructions import Reconstruction

UNIT_SCALE: Final[float] = 1.0


def effective_scale(reconstruction: Reconstruction) -> float:
    """How much a conversion scaled its sound before matching it: the working level times the load scale.

    A conversion matching the sound at the level the channels play it reads one, and a frame it plays
    times this scale is the level the sound itself holds. A record that left its load scale unmeasured
    counts it as one.
    """
    return reconstruction.coefficient * (reconstruction.stems_data.scale or UNIT_SCALE)
