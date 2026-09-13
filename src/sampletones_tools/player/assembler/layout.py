from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Final, Tuple

from sampletones_player.specification.driver import DRIVER_BINARY_DIRECTORY
from sampletones_shared.paths.source import SOURCE_ROOT

ASSEMBLY_PACKAGE: Final[str] = "sampletones_tools.player.assembly"
INCLUDE_DIRECTORY: Final[str] = "include"
SOURCE_DIRECTORY: Final[str] = "source"
LINKER_CONFIGURATION: Final[str] = "nsf.cfg"
SOURCE_NAMES: Final[Tuple[str, ...]] = ("driver.s", "clock.s", "channels.s")
BINARY_DIRECTORY: Final[Path] = SOURCE_ROOT / "sampletones_player" / "driver" / DRIVER_BINARY_DIRECTORY


def assembly() -> Traversable:
    """The assembly sources, their includes and the linker configuration, read from the package."""
    return files(ASSEMBLY_PACKAGE)
