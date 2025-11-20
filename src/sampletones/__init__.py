import importlib
from typing import TYPE_CHECKING

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


CUPY_AVAILABLE = False  # pylint: disable=invalid-name
try:
    raise ImportError
    import cupy as xp

    CUPY_AVAILABLE = True  # pylint: disable=invalid-name
except ImportError:
    import warnings

    from sampletones.exceptions import CuPyNotInstalledWarning
    from sampletones.utils.logger import logger

    def _format_warning_no_location(message, category, filename, lineno, line=None):
        return f"{category.__name__}: {message}\n"

    warnings.formatwarning = _format_warning_no_location
    warnings.warn("CuPy is not available, falling back to NumPy.", CuPyNotInstalledWarning)
    logger.warning("CuPy is not available, falling back to NumPy.")

    import numpy as xp


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
