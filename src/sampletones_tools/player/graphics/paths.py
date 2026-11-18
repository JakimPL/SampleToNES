from pathlib import Path
from typing import Final

from sampletones_player.specification.shell import SHELL_BINARY_DIRECTORY
from sampletones_shared.paths.package import package_directory
from sampletones_shared.paths.source import SOURCE_ROOT

CONFIG_DIRECTORY: Final[Path] = package_directory("sampletones_tools.player.graphics.config")
FONT_PATH: Final[Path] = CONFIG_DIRECTORY / "font.yaml"
SHAPES_PATH: Final[Path] = CONFIG_DIRECTORY / "shapes.yaml"
SHEET_PATH: Final[Path] = CONFIG_DIRECTORY / "sheet.yaml"
SCREEN_PATH: Final[Path] = CONFIG_DIRECTORY / "screen.yaml"
COLORS_PATH: Final[Path] = CONFIG_DIRECTORY / "colors.yaml"

PATTERNS_DIRECTORY: Final[Path] = SOURCE_ROOT / "sampletones_player" / "shell" / SHELL_BINARY_DIRECTORY
