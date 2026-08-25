from pathlib import Path
from typing import Final, Tuple

from sampletones_player.specification.driver import DRIVER_BINARY_DIRECTORY
from sampletones_shared.paths.source import SOURCE_ROOT

DRIVER_DIRECTORY: Final[Path] = SOURCE_ROOT / "sampletones_player" / "driver"
ASSEMBLY_DIRECTORY: Final[Path] = DRIVER_DIRECTORY / "assembly"
INCLUDE_DIRECTORY: Final[Path] = ASSEMBLY_DIRECTORY / "include"
SOURCE_DIRECTORY: Final[Path] = ASSEMBLY_DIRECTORY / "source"
LINKER_CONFIGURATION: Final[Path] = ASSEMBLY_DIRECTORY / "nsf.cfg"
BINARY_DIRECTORY: Final[Path] = DRIVER_DIRECTORY / DRIVER_BINARY_DIRECTORY

SOURCE_NAMES: Final[Tuple[str, ...]] = ("driver.s", "clock.s", "channels.s")
