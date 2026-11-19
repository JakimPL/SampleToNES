from pathlib import Path
from typing import Final, Tuple

from sampletones_player.specification.driver import DRIVER_BINARY_DIRECTORY
from sampletones_player.specification.shell import SHELL_BINARY_DIRECTORY
from sampletones_shared.paths.package import package_directory
from sampletones_shared.paths.source import SOURCE_ROOT

ASSEMBLY_PACKAGE: Final[str] = "sampletones_tools.player.assembly"
INCLUDE_DIRECTORY: Final[str] = "include"
SOURCE_DIRECTORY: Final[str] = "source"
LINKER_CONFIGURATION: Final[str] = "nsf.cfg"
SOURCE_NAMES: Final[Tuple[str, ...]] = ("driver.s", "clock.s", "channels.s")
SHELL_CONFIGURATION: Final[str] = "rom.cfg"
DECK_INCLUDE_NAME: Final[str] = "deck.inc"
DECK_SOURCE_NAME: Final[str] = "deck.s"
SHELL_SOURCE_NAMES: Final[Tuple[str, ...]] = ("shell.s", DECK_SOURCE_NAME)
BINARY_DIRECTORY: Final[Path] = SOURCE_ROOT / "sampletones_player" / "driver" / DRIVER_BINARY_DIRECTORY
SHELL_DIRECTORY: Final[Path] = SOURCE_ROOT / "sampletones_player" / "shell" / SHELL_BINARY_DIRECTORY
ASSEMBLY_DIRECTORY: Final[Path] = package_directory(ASSEMBLY_PACKAGE)
