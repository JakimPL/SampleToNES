import importlib
from typing import TYPE_CHECKING

CUPY_AVAILABLE = False  # pylint: disable=invalid-name
try:
    import cupy as xp

    CUPY_AVAILABLE = True  # pylint: disable=invalid-name
except ImportError:
    import numpy as xp  # pylint: disable=reimported,ungrouped-imports


if TYPE_CHECKING:
    from .configs import Config
    from .constants.application import SAMPLETONES_VERSION as __version__
    from .constants.enums import GeneratorName
    from .ffts import Window
    from .generators import Generator, NoiseGenerator, PulseGenerator, TriangleGenerator
    from .instructions import (
        Instruction,
        NoiseInstruction,
        PulseInstruction,
        TriangleInstruction,
    )
    from .library import Library
    from .reconstruction import Reconstruction, Reconstructor


def __getattr__(name):
    if name == "Config":
        from .configs import Config

        return Config

    if name == "__version__":
        from .constants.application import SAMPLETONES_VERSION

        return SAMPLETONES_VERSION

    if name == "GeneratorName":
        from .constants.enums import GeneratorName

        return GeneratorName

    if name == "Window":
        from .ffts import Window

        return Window

    if name in ("Generator", "NoiseGenerator", "PulseGenerator", "TriangleGenerator"):
        module = importlib.import_module(".generators", __package__)
        return getattr(module, name)

    if name in ("Instruction", "NoiseInstruction", "PulseInstruction", "TriangleInstruction"):
        module = importlib.import_module(".instructions", __package__)
        return getattr(module, name)

    if name in ("Reconstruction", "Reconstructor"):
        module = importlib.import_module(".reconstruction", __package__)
        return getattr(module, name)

    if name == "Library":
        from .library import Library

        return Library

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Config",
    "Window",
    "Library",
    "Reconstruction",
    "Reconstructor",
    "Generator",
    "PulseGenerator",
    "TriangleGenerator",
    "NoiseGenerator",
    "Instruction",
    "PulseInstruction",
    "TriangleInstruction",
    "NoiseInstruction",
    "GeneratorName",
    "__version__",
    "xp",
    "CUPY_AVAILABLE",
]


def __dir__():
    return sorted(__all__)
