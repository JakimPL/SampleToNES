from pathlib import Path
from typing import Final

from sampletones_shared.paths.package import package_directory
from sampletones_tools.player.assembler.layout import SHELL_DIRECTORY

CONFIG_DIRECTORY: Final[Path] = package_directory("sampletones_tools.player.graphics.config")
FONT_PATH: Final[Path] = CONFIG_DIRECTORY / "font.yaml"
SHAPES_PATH: Final[Path] = CONFIG_DIRECTORY / "shapes.yaml"
SHEET_PATH: Final[Path] = CONFIG_DIRECTORY / "sheet.yaml"
SCREEN_PATH: Final[Path] = CONFIG_DIRECTORY / "screen.yaml"
COLORS_PATH: Final[Path] = CONFIG_DIRECTORY / "colors.yaml"

PATTERNS_DIRECTORY: Final[Path] = SHELL_DIRECTORY
