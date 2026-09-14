from typing import Final

from sampletones_core.configs import Config
from sampletones_core.constants.enums import SpectrumMethod
from sampletones_core.instructions import PulseInstruction

LIBRARY_TONE: Final[PulseInstruction] = PulseInstruction(on=True, pitch=57, volume=12, duty_cycle=2)
REPAIR_TOLERANCE: Final[float] = 1e-4


def analyzed_config(method: SpectrumMethod, *, gamma: int) -> Config:
    """The default configuration analyzing audio by ``method`` through the transform at ``gamma``."""
    base = Config()
    library = base.library.model_copy(update={"spectrum_method": method, "transformation_gamma": gamma})
    return base.model_copy(update={"library": library})
