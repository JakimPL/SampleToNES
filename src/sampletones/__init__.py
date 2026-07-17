import importlib
from typing import TYPE_CHECKING, Any, List

if TYPE_CHECKING:
    from sampletones_core.configs import Config
    from sampletones_core.constants.enums import GeneratorName
    from sampletones_core.fft import Window
    from sampletones_core.generators import (
        Generator,
        NoiseGenerator,
        PulseGenerator,
        TriangleGenerator,
    )
    from sampletones_core.instructions import (
        Instruction,
        NoiseInstruction,
        PulseInstruction,
        TriangleInstruction,
    )
    from sampletones_core.library import InstructionLibrary
    from sampletones_core.reconstructions import Reconstruction, Reconstructor
    from sampletones_shared.application import SAMPLETONES_VERSION as __version__


def __getattr__(name: str) -> Any:
    if name == "Config":
        from sampletones_core.configs import Config

        return Config

    if name == "__version__":
        from sampletones_shared.application import SAMPLETONES_VERSION

        return SAMPLETONES_VERSION

    if name == "GeneratorName":
        from sampletones_core.constants.enums import GeneratorName

        return GeneratorName

    if name == "Window":
        from sampletones_core.fft import Window

        return Window

    if name in (
        "Generator",
        "NoiseGenerator",
        "PulseGenerator",
        "TriangleGenerator",
    ):
        module = importlib.import_module("sampletones_core.generators")
        return getattr(module, name)

    if name in (
        "Instruction",
        "NoiseInstruction",
        "PulseInstruction",
        "TriangleInstruction",
    ):
        module = importlib.import_module("sampletones_core.instructions")
        return getattr(module, name)

    if name in ("Reconstruction", "Reconstructor"):
        module = importlib.import_module("sampletones_core.reconstructions")
        return getattr(module, name)

    if name == "InstructionLibrary":
        from sampletones_core.library import InstructionLibrary

        return InstructionLibrary

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Config",
    "Window",
    "InstructionLibrary",
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


def __dir__() -> List[str]:
    return sorted(__all__)
