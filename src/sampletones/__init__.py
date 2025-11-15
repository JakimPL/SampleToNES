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
]


def __dir__():
    return sorted(__all__)
